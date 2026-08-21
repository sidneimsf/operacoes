from datetime import date, datetime, time, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

import jwt
from database import get_db
from models import Aviso, Chamado, Cliente, Colaborador, Empresa, Usuario
from schemas import AvisoCreate, ChamadoCreate, ChamadoFinalizar, ChamadoStatusUpdate, LoginRequest, TokenResponse
from security import criar_token, decodificar_token, verificar_senha

app = FastAPI(title="Operacoes SolarSync", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

seguranca = HTTPBearer()

TIPOS_CHAMADO = [
    {"chave": "manutencao", "label": "Manutenção corretiva"},
    {"chave": "material_limpeza", "label": "Material de limpeza"},
    {"chave": "uniforme", "label": "Uniforme / EPI"},
    {"chave": "documento", "label": "Entrega de documento"},
    {"chave": "folha_ponto", "label": "Folha de ponto"},
    {"chave": "reclamacao", "label": "Reclamação do cliente"},
    {"chave": "seguranca", "label": "Acidente / segurança"},
    {"chave": "comercial", "label": "Solicitação comercial"},
    {"chave": "outros", "label": "Outros"},
]
CHAVES_TIPO_VALIDAS = {t["chave"] for t in TIPOS_CHAMADO}

STATUS_CHAMADO = [
    {"chave": "novo", "label": "Novo"},
    {"chave": "em_andamento", "label": "Em aberto"},
    {"chave": "finalizado", "label": "Finalizado"},
]
CHAVES_STATUS_VALIDAS = {s["chave"] for s in STATUS_CHAMADO}

PRIORIDADES_CHAMADO = [
    {"chave": "normal", "label": "Normal"},
    {"chave": "urgente", "label": "Urgente"},
    {"chave": "urgentissimo", "label": "Urgentíssimo"},
]
CHAVES_PRIORIDADE_VALIDAS = {p["chave"] for p in PRIORIDADES_CHAMADO}


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(seguranca),
    db: Session = Depends(get_db),
) -> Usuario:
    try:
        payload = decodificar_token(credenciais.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada, faca login novamente")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado ou inativo")
    return usuario


def exigir_papel(*papeis_permitidos: str):
    """Dependencia que restringe uma rota a determinados papeis (ex: so escritorio)."""
    def verificador(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.papel not in papeis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao tem permissao para acessar este recurso",
            )
        return usuario
    return verificador


def serializar_chamado(c: Chamado) -> dict:
    return {
        "id": c.id,
        "cliente_id": c.cliente_id,
        "cliente_nome": c.cliente.nome,
        "empresa_id": c.cliente.empresa_id,
        "tipo": c.tipo,
        "prioridade": c.prioridade,
        "descricao": c.descricao,
        "status": c.status,
        "aberto_por": c.aberto_por.nome,
        "responsavel_id": c.responsavel_id,
        "responsavel_nome": c.responsavel.nome if c.responsavel else None,
        "criado_em": c.criado_em.isoformat(),
        "finalizado_em": c.finalizado_em.isoformat() if c.finalizado_em else None,
        "finalizado_por": c.finalizado_por.nome if c.finalizado_por else None,
        "confirmacao_vista": c.confirmacao_vista,
        "fechamento": (
            {
                "pendencia": c.fechamento_pendencia,
                "pendencia_detalhe": c.fechamento_pendencia_detalhe,
                "documento_enviado": c.fechamento_documento_enviado,
                "documento_detalhe": c.fechamento_documento_detalhe,
                "observacoes": c.fechamento_observacoes,
            }
            if c.status == "finalizado"
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Basico / paginas publicas
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"app": "operacoes.solarsync", "status": "em desenvolvimento"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def estatisticas_publicas(db: Session = Depends(get_db)):
    """Contagens gerais, sem dados sensiveis - usado no painel de status da tela de login."""
    return {
        "empresas": db.query(Empresa).count(),
        "clientes": db.query(Cliente).count(),
    }


@app.get("/login", include_in_schema=False)
def pagina_login():
    return FileResponse("static/login.html")


@app.get("/painel", include_in_schema=False)
def pagina_painel_legado():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", include_in_schema=False)
def pagina_dashboard():
    return FileResponse("static/dashboard.html")


@app.get("/clientes", include_in_schema=False)
def pagina_clientes():
    return FileResponse("static/clientes.html")


@app.get("/colaboradores", include_in_schema=False)
def pagina_colaboradores():
    return FileResponse("static/colaboradores.html")


@app.get("/usuarios", include_in_schema=False)
def pagina_usuarios():
    return FileResponse("static/usuarios.html")


@app.get("/ocorrencias", include_in_schema=False)
def pagina_ocorrencias():
    return FileResponse("static/ocorrencias.html")


@app.get("/avisos", include_in_schema=False)
def pagina_avisos():
    return FileResponse("static/avisos.html")


@app.get("/cliente-detalhe", include_in_schema=False)
def pagina_cliente_detalhe():
    return FileResponse("static/cliente-detalhe.html")


@app.get("/ponto", include_in_schema=False)
@app.get("/documentos", include_in_schema=False)
@app.get("/uniformes", include_in_schema=False)
def paginas_legado_redirecionam_para_ocorrencias():
    """Esses modulos viraram tipos de chamado - a tela de Ocorrencias e' onde eles agora vivem."""
    return RedirectResponse(url="/ocorrencias")


# ---------------------------------------------------------------------------
# Autenticacao
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=TokenResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter_by(email=dados.email.lower().strip()).first()
    if usuario is None or not usuario.ativo or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha invalidos")

    token = criar_token(usuario.id, usuario.papel)
    return TokenResponse(access_token=token, id=usuario.id, nome=usuario.nome, papel=usuario.papel)


@app.get("/auth/me")
def quem_sou_eu(usuario: Usuario = Depends(usuario_atual)):
    return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email, "papel": usuario.papel}


# ---------------------------------------------------------------------------
# API - dados
# ---------------------------------------------------------------------------

@app.get("/dashboard/resumo")
def resumo_dashboard(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Indicadores gerais para a tela inicial, calculados a partir de dados reais."""
    total_empresas = db.query(Empresa).count()
    total_clientes = db.query(Cliente).count()
    total_colaboradores = db.query(Colaborador).count()
    total_usuarios = db.query(Usuario).filter_by(ativo=True).count()
    total_chamados_abertos = db.query(Chamado).filter(Chamado.status != "finalizado").count()

    empresas = db.query(Empresa).order_by(Empresa.nome).all()
    clientes_por_empresa = [
        {"empresa": e.nome, "total": db.query(Cliente).filter_by(empresa_id=e.id).count()}
        for e in empresas
    ]

    resposta = {
        "total_empresas": total_empresas,
        "total_clientes": total_clientes,
        "total_colaboradores": total_colaboradores,
        "total_usuarios": total_usuarios,
        "total_chamados_abertos": total_chamados_abertos,
        "clientes_por_empresa": clientes_por_empresa,
    }

    if usuario.papel == "supervisor":
        meus_chamados = (
            db.query(Chamado)
            .filter(Chamado.responsavel_id == usuario.id, Chamado.status != "finalizado")
            .order_by(Chamado.criado_em.desc())
            .all()
        )
        resposta["meus_chamados"] = [serializar_chamado(c) for c in meus_chamados]

    chamados_para_confirmar = (
        db.query(Chamado)
        .filter(
            Chamado.aberto_por_id == usuario.id,
            Chamado.status == "finalizado",
            Chamado.confirmacao_vista.is_(False),
        )
        .order_by(Chamado.finalizado_em.desc())
        .all()
    )
    if chamados_para_confirmar:
        resposta["chamados_para_confirmar"] = [serializar_chamado(c) for c in chamados_para_confirmar]

    return resposta


@app.get("/empresas")
def listar_empresas(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    empresas = db.query(Empresa).order_by(Empresa.nome).all()
    return [{"id": e.id, "nome": e.nome} for e in empresas]


@app.get("/clientes-dados")
def listar_clientes(
    empresa_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    query = db.query(Cliente)
    if empresa_id is not None:
        query = query.filter(Cliente.empresa_id == empresa_id)
    clientes = query.order_by(Cliente.nome).all()
    return [
        {"id": c.id, "nome": c.nome, "empresa_id": c.empresa_id, "cnpj": c.cnpj}
        for c in clientes
    ]


@app.get("/clientes-dados/{cliente_id}")
def detalhe_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")
    return {
        "id": cliente.id,
        "nome": cliente.nome,
        "cnpj": cliente.cnpj,
        "empresa_id": cliente.empresa_id,
        "empresa_nome": cliente.empresa.nome,
    }


def serializar_colaborador(c: Colaborador) -> dict:
    return {
        "id": c.id,
        "registro": c.registro,
        "nome": c.nome,
        "cargo": c.cargo,
        "contato": c.contato,
        "data_admissao": c.data_admissao.isoformat() if c.data_admissao else None,
        "empresa_id": c.empresa_id,
        "empresa_nome": c.empresa.nome,
        "supervisor_id": c.supervisor_id,
        "supervisor_nome": c.supervisor.nome if c.supervisor else None,
        "status": c.status,
    }


@app.get("/colaboradores-dados")
def listar_colaboradores(
    empresa_id: int | None = None,
    supervisor_id: int | None = None,
    status_filtro: str | None = None,
    cargo: str | None = None,
    busca: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    query = db.query(Colaborador)
    if empresa_id is not None:
        query = query.filter(Colaborador.empresa_id == empresa_id)
    if supervisor_id is not None:
        query = query.filter(Colaborador.supervisor_id == supervisor_id)
    if status_filtro:
        query = query.filter(Colaborador.status == status_filtro)
    if cargo:
        query = query.filter(Colaborador.cargo == cargo)
    if busca:
        query = query.filter(Colaborador.nome.ilike(f"%{busca}%"))
    colaboradores = query.order_by(Colaborador.nome).all()
    return [serializar_colaborador(c) for c in colaboradores]


@app.get("/colaboradores-dados/resumo")
def resumo_colaboradores(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Indicadores executivos: total, ativos, afastados, admitidos no mes, e quebras por empresa/supervisor/cargo."""
    total = db.query(Colaborador).count()
    ativos = db.query(Colaborador).filter_by(status="ativo").count()
    afastados = db.query(Colaborador).filter_by(status="afastado").count()

    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    admitidos_mes = db.query(Colaborador).filter(Colaborador.data_admissao >= inicio_mes).count()

    empresas = db.query(Empresa).order_by(Empresa.nome).all()
    por_empresa = [
        {"empresa": e.nome, "total": db.query(Colaborador).filter_by(empresa_id=e.id).count()}
        for e in empresas
    ]

    supervisores = db.query(Usuario).filter_by(papel="supervisor", ativo=True).order_by(Usuario.nome).all()
    por_supervisor = [
        {"supervisor": s.nome, "total": db.query(Colaborador).filter_by(supervisor_id=s.id).count()}
        for s in supervisores
    ]
    sem_supervisor = db.query(Colaborador).filter(Colaborador.supervisor_id.is_(None)).count()
    if sem_supervisor:
        por_supervisor.append({"supervisor": "Administrativo / sem supervisor", "total": sem_supervisor})

    cargos_query = (
        db.query(Colaborador.cargo, func.count(Colaborador.id))
        .group_by(Colaborador.cargo)
        .order_by(func.count(Colaborador.id).desc())
        .all()
    )
    por_cargo = [{"cargo": cargo or "Não informado", "total": total} for cargo, total in cargos_query]

    return {
        "total": total,
        "ativos": ativos,
        "afastados": afastados,
        "admitidos_mes": admitidos_mes,
        "por_empresa": por_empresa,
        "por_supervisor": por_supervisor,
        "por_cargo": por_cargo,
    }


@app.get("/usuarios-dados")
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_papel("escritorio")),
):
    usuarios = db.query(Usuario).order_by(Usuario.nome).all()
    return [
        {"id": u.id, "nome": u.nome, "email": u.email, "papel": u.papel, "ativo": u.ativo}
        for u in usuarios
    ]


@app.get("/supervisores")
def listar_supervisores(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Lista enxuta (id + nome) dos supervisores ativos, usada para atribuir responsavel a um chamado."""
    supervisores = db.query(Usuario).filter_by(papel="supervisor", ativo=True).order_by(Usuario.nome).all()
    return [{"id": s.id, "nome": s.nome} for s in supervisores]


@app.get("/pessoas")
def listar_pessoas(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Lista enxuta (id + nome + papel) de todos os usuarios ativos, usada para escolher destinatario de aviso."""
    pessoas = db.query(Usuario).filter_by(ativo=True).order_by(Usuario.nome).all()
    return [{"id": p.id, "nome": p.nome, "papel": p.papel} for p in pessoas]


def serializar_aviso(a: Aviso) -> dict:
    return {
        "id": a.id,
        "mensagem": a.mensagem,
        "criado_por_id": a.criado_por_id,
        "criado_por_nome": a.criado_por.nome,
        "destinatario_id": a.destinatario_id,
        "destinatario_nome": a.destinatario.nome if a.destinatario else None,
        "criado_em": a.criado_em.isoformat(),
    }


@app.get("/avisos-dados/nao-lidos")
def contar_avisos_nao_lidos(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    query = (
        db.query(Aviso)
        .filter((Aviso.destinatario_id.is_(None)) | (Aviso.destinatario_id == usuario.id))
        .filter(Aviso.criado_por_id != usuario.id)
    )
    if usuario.avisos_vistos_em is not None:
        query = query.filter(Aviso.criado_em > usuario.avisos_vistos_em)
    return {"total": query.count()}


@app.post("/avisos-dados/marcar-vistos")
def marcar_avisos_vistos(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    usuario.avisos_vistos_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@app.post("/avisos-dados", status_code=status.HTTP_201_CREATED)
def criar_aviso(
    dados: AvisoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    mensagem = dados.mensagem.strip()
    if not mensagem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escreva uma mensagem")

    if dados.destinatario_id is not None:
        destinatario = db.get(Usuario, dados.destinatario_id)
        if destinatario is None or not destinatario.ativo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Destinatario invalido")

    aviso = Aviso(
        mensagem=mensagem,
        criado_por_id=usuario.id,
        destinatario_id=dados.destinatario_id,
    )
    db.add(aviso)
    db.commit()
    db.refresh(aviso)
    return serializar_aviso(aviso)


@app.get("/avisos-dados")
def listar_avisos(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Mostra avisos para todos, avisos dirigidos a mim, e avisos que eu mesmo criei."""
    avisos = (
        db.query(Aviso)
        .filter(
            (Aviso.destinatario_id.is_(None))
            | (Aviso.destinatario_id == usuario.id)
            | (Aviso.criado_por_id == usuario.id)
        )
        .order_by(Aviso.criado_em.desc())
        .all()
    )
    return [serializar_aviso(a) for a in avisos]


@app.get("/chamados-tipos")
def tipos_e_status_chamado(usuario: Usuario = Depends(usuario_atual)):
    return {"tipos": TIPOS_CHAMADO, "status": STATUS_CHAMADO, "prioridades": PRIORIDADES_CHAMADO}


@app.post("/chamados-dados", status_code=status.HTTP_201_CREATED)
def abrir_chamado(
    dados: ChamadoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if dados.tipo not in CHAVES_TIPO_VALIDAS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de chamado invalido")

    if dados.prioridade not in CHAVES_PRIORIDADE_VALIDAS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prioridade invalida")

    cliente = db.get(Cliente, dados.cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")

    responsavel = db.get(Usuario, dados.responsavel_id)
    if responsavel is None or responsavel.papel != "supervisor" or not responsavel.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Responsavel invalido")

    descricao = dados.descricao.strip()
    if not descricao:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Descreva o chamado")

    chamado = Chamado(
        cliente_id=dados.cliente_id,
        tipo=dados.tipo,
        prioridade=dados.prioridade,
        descricao=descricao,
        status="novo",
        aberto_por_id=usuario.id,
        responsavel_id=dados.responsavel_id,
    )
    db.add(chamado)
    db.commit()
    db.refresh(chamado)
    return serializar_chamado(chamado)


@app.get("/chamados-dados")
def listar_chamados(
    status_filtro: str | None = None,
    tipo: str | None = None,
    prioridade: str | None = None,
    cliente_id: int | None = None,
    empresa_id: int | None = None,
    responsavel_id: int | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    query = db.query(Chamado).join(Cliente)

    if status_filtro == "aberto":
        query = query.filter(Chamado.status != "finalizado")
    elif status_filtro:
        query = query.filter(Chamado.status == status_filtro)
    if tipo:
        query = query.filter(Chamado.tipo == tipo)
    if prioridade:
        query = query.filter(Chamado.prioridade == prioridade)
    if cliente_id:
        query = query.filter(Chamado.cliente_id == cliente_id)
    if empresa_id:
        query = query.filter(Cliente.empresa_id == empresa_id)
    if responsavel_id:
        query = query.filter(Chamado.responsavel_id == responsavel_id)
    if data_inicio:
        inicio_dt = datetime.combine(date.fromisoformat(data_inicio), time.min, tzinfo=timezone.utc)
        query = query.filter(Chamado.criado_em >= inicio_dt)
    if data_fim:
        fim_dt = datetime.combine(date.fromisoformat(data_fim), time.max, tzinfo=timezone.utc)
        query = query.filter(Chamado.criado_em <= fim_dt)

    chamados = query.order_by(Chamado.criado_em.desc()).all()
    return [serializar_chamado(c) for c in chamados]


@app.patch("/chamados-dados/{chamado_id}")
def atualizar_status_chamado(
    chamado_id: int,
    dados: ChamadoStatusUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if dados.status not in CHAVES_STATUS_VALIDAS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status invalido")
    if dados.status == "finalizado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para finalizar, preencha o checklist de encerramento",
        )

    chamado = db.get(Chamado, chamado_id)
    if chamado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chamado nao encontrado")

    chamado.status = dados.status
    db.commit()
    db.refresh(chamado)
    return serializar_chamado(chamado)


@app.post("/chamados-dados/{chamado_id}/finalizar")
def finalizar_chamado(
    chamado_id: int,
    dados: ChamadoFinalizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    chamado = db.get(Chamado, chamado_id)
    if chamado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chamado nao encontrado")
    if chamado.status == "finalizado":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chamado ja esta finalizado")

    if dados.pendencia and not (dados.pendencia_detalhe or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Descreva a pendencia")
    if dados.documento_enviado and not (dados.documento_detalhe or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe qual documento foi enviado")

    chamado.status = "finalizado"
    chamado.finalizado_em = datetime.now(timezone.utc)
    chamado.finalizado_por_id = usuario.id
    chamado.confirmacao_vista = False
    chamado.fechamento_pendencia = dados.pendencia
    chamado.fechamento_pendencia_detalhe = (dados.pendencia_detalhe or "").strip() or None
    chamado.fechamento_documento_enviado = dados.documento_enviado
    chamado.fechamento_documento_detalhe = (dados.documento_detalhe or "").strip() or None
    chamado.fechamento_observacoes = (dados.observacoes or "").strip() or None

    db.commit()
    db.refresh(chamado)
    return serializar_chamado(chamado)


@app.post("/chamados-dados/{chamado_id}/confirmar")
def confirmar_chamado_finalizado(
    chamado_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    chamado = db.get(Chamado, chamado_id)
    if chamado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chamado nao encontrado")
    if chamado.status != "finalizado":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chamado ainda nao foi finalizado")

    chamado.confirmacao_vista = True
    db.commit()
    db.refresh(chamado)
    return serializar_chamado(chamado)


# Estrutura prevista para os proximos modulos:
#   /avisos-dados      -> mural de avisos entre escritorio e supervisores
