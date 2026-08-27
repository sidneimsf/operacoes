import os
import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

import jwt
from alertas_aso import verificar_e_enviar_alertas
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal, get_db
from models import (
    Aviso,
    Chamado,
    Cliente,
    Colaborador,
    ColaboradorEvento,
    Empresa,
    HorarioServico,
    ManutencaoVeiculo,
    Usuario,
    UsuarioPermissao,
    Veiculo,
)
from schemas import (
    AvisoCreate,
    ChamadoCreate,
    ChamadoFinalizar,
    ChamadoStatusUpdate,
    ClienteCreate,
    ClienteUpdate,
    ColaboradorCreate,
    ColaboradorEventoUpdate,
    ColaboradorUpdate,
    HorarioServicoCreate,
    HorarioServicoUpdate,
    LoginRequest,
    ManutencaoVeiculoCreate,
    ManutencaoVeiculoUpdate,
    PermissaoUpdate,
    TokenResponse,
    VeiculoCreate,
    VeiculoUpdate,
)
from security import criar_token, decodificar_token, verificar_senha

app = FastAPI(title="Operacoes SolarSync", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

seguranca = HTTPBearer()


def job_verificar_asos():
    """Roda em background, uma vez por dia - usa sua propria sessao de banco."""
    db = SessionLocal()
    try:
        resultado = verificar_e_enviar_alertas(db)
        print("[alerta-aso]", resultado)
    except Exception as erro:
        print("[alerta-aso] erro ao verificar/enviar:", erro)
    finally:
        db.close()


agendador = BackgroundScheduler()
agendador.add_job(job_verificar_asos, "cron", hour=8, minute=0)
agendador.start()

PASTA_UPLOADS = Path("uploads/colaboradores")
PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)

EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".pdf"}
TAMANHO_MAXIMO_ARQUIVO = 10 * 1024 * 1024  # 10 MB

TIPOS_EVENTO_COLABORADOR = [
    {"chave": "anotacao", "label": "Anotação"},
    {"chave": "documento", "label": "Documento"},
    {"chave": "atestado", "label": "Atestado médico"},
    {"chave": "aso", "label": "ASO (exame ocupacional)"},
    {"chave": "falta", "label": "Falta"},
    {"chave": "cobertura", "label": "Cobriu falta"},
    {"chave": "ferias", "label": "Férias"},
    {"chave": "advertencia", "label": "Advertência"},
    {"chave": "outros", "label": "Outros"},
]
CHAVES_TIPO_EVENTO_VALIDAS = {t["chave"] for t in TIPOS_EVENTO_COLABORADOR}

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


# ---------------------------------------------------------------------------
# Permissoes configuraveis por usuario (alem do papel padrao)
# ---------------------------------------------------------------------------

MODULOS_PERMISSAO = [
    {"chave": "veiculos", "label": "Veículos", "padrao_escritorio_apenas": True},
    {"chave": "asos", "label": "ASOs", "padrao_escritorio_apenas": True},
    {"chave": "usuarios", "label": "Usuários (gerenciar contas)", "padrao_escritorio_apenas": True},
    {"chave": "criar_cliente", "label": "Criar/editar clientes", "padrao_escritorio_apenas": True},
    {"chave": "criar_colaborador", "label": "Criar/editar colaboradores", "padrao_escritorio_apenas": True},
]
CHAVES_MODULOS_VALIDAS = {m["chave"] for m in MODULOS_PERMISSAO}


def tem_permissao(db: Session, usuario: Usuario, modulo: str) -> bool:
    """
    Um override explicito (criado por um super_admin) sempre vale por
    cima da regra padrao do modulo. Sem override, usa a regra padrao:
    modulos marcados como 'padrao_escritorio_apenas' exigem papel
    escritorio; os demais ficam liberados pra qualquer usuario logado.
    """
    override = (
        db.query(UsuarioPermissao)
        .filter_by(usuario_id=usuario.id, modulo=modulo)
        .first()
    )
    if override is not None:
        return override.habilitado

    info_modulo = next((m for m in MODULOS_PERMISSAO if m["chave"] == modulo), None)
    if info_modulo is not None and info_modulo["padrao_escritorio_apenas"]:
        return usuario.papel == "escritorio"
    return True


def exigir_modulo(modulo: str):
    """Dependencia que checa a permissao efetiva (override ou padrao) para um modulo."""
    def verificador(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if not tem_permissao(db, usuario, modulo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao tem permissao para acessar esta area",
            )
        return usuario
    return verificador


def exigir_super_admin(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if not usuario.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem acessar isso",
        )
    return usuario


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


@app.get("/asos", include_in_schema=False)
def pagina_asos():
    return FileResponse("static/asos.html")


@app.get("/veiculos", include_in_schema=False)
def pagina_veiculos():
    return FileResponse("static/veiculos.html")


@app.get("/veiculo-detalhe", include_in_schema=False)
def pagina_veiculo_detalhe():
    return FileResponse("static/veiculo-detalhe.html")


@app.get("/permissoes", include_in_schema=False)
def pagina_permissoes():
    return FileResponse("static/permissoes.html")


@app.get("/ocorrencias", include_in_schema=False)
def pagina_ocorrencias():
    return FileResponse("static/ocorrencias.html")


@app.get("/avisos", include_in_schema=False)
def pagina_avisos():
    return FileResponse("static/avisos.html")


@app.get("/cliente-detalhe", include_in_schema=False)
def pagina_cliente_detalhe():
    return FileResponse("static/cliente-detalhe.html")


@app.get("/colaborador-detalhe", include_in_schema=False)
def pagina_colaborador_detalhe():
    return FileResponse("static/colaborador-detalhe.html")


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
    return TokenResponse(
        access_token=token, id=usuario.id, nome=usuario.nome, papel=usuario.papel, super_admin=usuario.super_admin
    )


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


def _calcular_anos_completos(data_inicio: date, referencia: date) -> int:
    anos = referencia.year - data_inicio.year
    if (referencia.month, referencia.day) < (data_inicio.month, data_inicio.day):
        anos -= 1
    return anos


@app.get("/colaboradores-dados/lembretes")
def lembretes_colaboradores(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Aniversariantes (nascimento) e aniversario de empresa (tempo de casa) do mes atual."""
    hoje = date.today()
    colaboradores = db.query(Colaborador).filter(Colaborador.status != "desligado").all()

    aniversarios_nascimento = []
    aniversarios_empresa = []

    for c in colaboradores:
        if c.aniversario_dia and c.aniversario_mes == hoje.month:
            aniversarios_nascimento.append(
                {
                    "colaborador_id": c.id,
                    "colaborador_nome": c.nome,
                    "empresa_nome": c.empresa.nome,
                    "dia": c.aniversario_dia,
                    "hoje": c.aniversario_dia == hoje.day,
                }
            )

        if c.data_admissao and c.data_admissao.month == hoje.month:
            anos = _calcular_anos_completos(c.data_admissao, date(hoje.year, c.data_admissao.month, c.data_admissao.day))
            aniversarios_empresa.append(
                {
                    "colaborador_id": c.id,
                    "colaborador_nome": c.nome,
                    "empresa_nome": c.empresa.nome,
                    "dia": c.data_admissao.day,
                    "anos_completos": anos,
                    "hoje": c.data_admissao.day == hoje.day,
                }
            )

    aniversarios_nascimento.sort(key=lambda x: x["dia"])
    aniversarios_empresa.sort(key=lambda x: x["dia"])

    return {
        "aniversarios_nascimento": aniversarios_nascimento,
        "aniversarios_empresa": aniversarios_empresa,
    }


def serializar_cliente(c: Cliente) -> dict:
    return {
        "id": c.id,
        "nome": c.nome,
        "cnpj": c.cnpj,
        "municipio": c.municipio,
        "endereco": c.endereco,
        "bairro": c.bairro,
        "cidade": c.cidade,
        "responsavel_nome": c.responsavel_nome,
        "responsavel_telefone": c.responsavel_telefone,
        "senha_acesso": c.senha_acesso,
        "chave_acesso": c.chave_acesso,
        "empresa_id": c.empresa_id,
        "empresa_nome": c.empresa.nome,
        "ativo": c.ativo,
    }


@app.get("/clientes-dados")
def listar_clientes(
    empresa_id: int | None = None,
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    query = db.query(Cliente)
    if empresa_id is not None:
        query = query.filter(Cliente.empresa_id == empresa_id)
    if not incluir_inativos:
        query = query.filter(Cliente.ativo.is_(True))
    clientes = query.order_by(Cliente.nome).all()
    return [
        {"id": c.id, "nome": c.nome, "empresa_id": c.empresa_id, "cnpj": c.cnpj, "ativo": c.ativo}
        for c in clientes
    ]


@app.post("/clientes-dados", status_code=status.HTTP_201_CREATED)
def criar_cliente(
    dados: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("criar_cliente")),
):
    empresa = db.get(Empresa, dados.empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa invalida")

    nome = dados.nome.strip()
    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome do cliente")

    cliente = Cliente(
        empresa_id=dados.empresa_id,
        nome=nome,
        cnpj=dados.cnpj.strip() if dados.cnpj else None,
        municipio=dados.municipio.strip() if dados.municipio else None,
        endereco=dados.endereco.strip() if dados.endereco else None,
        bairro=dados.bairro.strip() if dados.bairro else None,
        cidade=dados.cidade.strip() if dados.cidade else None,
        responsavel_nome=dados.responsavel_nome.strip() if dados.responsavel_nome else None,
        responsavel_telefone=dados.responsavel_telefone.strip() if dados.responsavel_telefone else None,
        senha_acesso=dados.senha_acesso.strip() if dados.senha_acesso else None,
        chave_acesso=dados.chave_acesso.strip() if dados.chave_acesso else None,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return serializar_cliente(cliente)


@app.get("/clientes-dados/{cliente_id}")
def detalhe_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")
    return serializar_cliente(cliente)


@app.patch("/clientes-dados/{cliente_id}")
def editar_cliente(
    cliente_id: int,
    dados: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")

    campos = dados.model_dump(exclude_unset=True)

    if "empresa_id" in campos:
        if db.get(Empresa, campos["empresa_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa invalida")
        cliente.empresa_id = campos["empresa_id"]
    if "nome" in campos:
        nome = (campos["nome"] or "").strip()
        if not nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome nao pode ficar vazio")
        cliente.nome = nome
    if "cnpj" in campos:
        cliente.cnpj = campos["cnpj"].strip() if campos["cnpj"] else None
    if "municipio" in campos:
        cliente.municipio = campos["municipio"].strip() if campos["municipio"] else None
    if "endereco" in campos:
        cliente.endereco = campos["endereco"].strip() if campos["endereco"] else None
    if "bairro" in campos:
        cliente.bairro = campos["bairro"].strip() if campos["bairro"] else None
    if "cidade" in campos:
        cliente.cidade = campos["cidade"].strip() if campos["cidade"] else None
    if "responsavel_nome" in campos:
        cliente.responsavel_nome = campos["responsavel_nome"].strip() if campos["responsavel_nome"] else None
    if "responsavel_telefone" in campos:
        cliente.responsavel_telefone = campos["responsavel_telefone"].strip() if campos["responsavel_telefone"] else None
    if "senha_acesso" in campos:
        cliente.senha_acesso = campos["senha_acesso"].strip() if campos["senha_acesso"] else None
    if "chave_acesso" in campos:
        cliente.chave_acesso = campos["chave_acesso"].strip() if campos["chave_acesso"] else None
    if "ativo" in campos:
        cliente.ativo = campos["ativo"]

    db.commit()
    db.refresh(cliente)
    return serializar_cliente(cliente)


def serializar_colaborador(c: Colaborador) -> dict:
    return {
        "id": c.id,
        "registro": c.registro,
        "nome": c.nome,
        "cargo": c.cargo,
        "contato": c.contato,
        "data_admissao": c.data_admissao.isoformat() if c.data_admissao else None,
        "aniversario_dia": c.aniversario_dia,
        "aniversario_mes": c.aniversario_mes,
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
    incluir_desligados: bool = False,
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
    elif not incluir_desligados:
        query = query.filter(Colaborador.status != "desligado")
    if cargo:
        query = query.filter(Colaborador.cargo == cargo)
    if busca:
        query = query.filter(Colaborador.nome.ilike(f"%{busca}%"))
    colaboradores = query.order_by(Colaborador.nome).all()
    return [serializar_colaborador(c) for c in colaboradores]


def _validar_aniversario(dia: int | None, mes: int | None) -> None:
    if (dia is None) != (mes is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe dia e mes do aniversario juntos, ou deixe os dois em branco",
        )
    if dia is not None and not (1 <= dia <= 31):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dia de aniversario invalido")
    if mes is not None and not (1 <= mes <= 12):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mes de aniversario invalido")


@app.post("/colaboradores-dados", status_code=status.HTTP_201_CREATED)
def criar_colaborador(
    dados: ColaboradorCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("criar_colaborador")),
):
    empresa = db.get(Empresa, dados.empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa invalida")

    nome = dados.nome.strip()
    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome do colaborador")

    if dados.status not in ("ativo", "afastado", "desligado"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status invalido")

    if dados.supervisor_id is not None and db.get(Usuario, dados.supervisor_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supervisor invalido")

    _validar_aniversario(dados.aniversario_dia, dados.aniversario_mes)

    admissao = date.fromisoformat(dados.data_admissao) if dados.data_admissao else None

    colaborador = Colaborador(
        empresa_id=dados.empresa_id,
        registro=dados.registro.strip() if dados.registro else None,
        nome=nome,
        cargo=dados.cargo.strip() if dados.cargo else None,
        contato=dados.contato.strip() if dados.contato else None,
        data_admissao=admissao,
        aniversario_dia=dados.aniversario_dia,
        aniversario_mes=dados.aniversario_mes,
        supervisor_id=dados.supervisor_id,
        status=dados.status,
    )
    db.add(colaborador)
    db.commit()
    db.refresh(colaborador)
    return serializar_colaborador(colaborador)


@app.get("/colaboradores-dados/resumo")
def resumo_colaboradores(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    """Indicadores executivos: total, ativos, afastados, admitidos no mes, e quebras por empresa/supervisor/cargo."""
    total = db.query(Colaborador).count()
    ativos = db.query(Colaborador).filter_by(status="ativo").count()
    afastados = db.query(Colaborador).filter_by(status="afastado").count()
    desligados = db.query(Colaborador).filter_by(status="desligado").count()

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

    eventos_atestado_ativos = (
        db.query(ColaboradorEvento)
        .filter(
            ColaboradorEvento.tipo == "atestado",
            ColaboradorEvento.data_inicio <= hoje,
            (ColaboradorEvento.data_fim >= hoje) | (ColaboradorEvento.data_fim.is_(None)),
        )
        .all()
    )
    lista_atestado = [
        {
            "colaborador_id": e.colaborador_id,
            "nome": e.colaborador.nome,
            "data_fim": e.data_fim.isoformat() if e.data_fim else None,
        }
        for e in eventos_atestado_ativos
    ]

    eventos_falta_hoje = (
        db.query(ColaboradorEvento)
        .filter(ColaboradorEvento.tipo == "falta", ColaboradorEvento.data_inicio == hoje)
        .all()
    )
    lista_faltantes = [
        {"colaborador_id": e.colaborador_id, "nome": e.colaborador.nome}
        for e in eventos_falta_hoje
    ]

    return {
        "total": total,
        "ativos": ativos,
        "afastados": afastados,
        "desligados": desligados,
        "admitidos_mes": admitidos_mes,
        "em_atestado": len(lista_atestado),
        "faltantes_hoje": len(lista_faltantes),
        "lista_atestado": lista_atestado,
        "lista_faltantes": lista_faltantes,
        "por_empresa": por_empresa,
        "por_supervisor": por_supervisor,
        "por_cargo": por_cargo,
    }


@app.get("/colaboradores-dados/eventos-tipos")
def tipos_evento_colaborador(usuario: Usuario = Depends(usuario_atual)):
    # "cobertura" nao aparece como opcao selecionavel - e' gerado automaticamente
    # quando alguem registra uma falta apontando quem cobriu.
    return {"tipos": [t for t in TIPOS_EVENTO_COLABORADOR if t["chave"] != "cobertura"]}


def serializar_evento_colaborador(e: ColaboradorEvento) -> dict:
    return {
        "id": e.id,
        "colaborador_id": e.colaborador_id,
        "tipo": e.tipo,
        "descricao": e.descricao,
        "data_inicio": e.data_inicio.isoformat() if e.data_inicio else None,
        "data_fim": e.data_fim.isoformat() if e.data_fim else None,
        "colaborador_relacionado_id": e.colaborador_relacionado_id,
        "colaborador_relacionado_nome": e.colaborador_relacionado.nome if e.colaborador_relacionado else None,
        "tem_arquivo": e.arquivo_path is not None,
        "arquivo_nome_original": e.arquivo_nome_original,
        "registrado_por": e.registrado_por.nome,
        "criado_em": e.criado_em.isoformat(),
    }


@app.get("/colaboradores-dados/{colaborador_id}")
def detalhe_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    c = db.get(Colaborador, colaborador_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador nao encontrado")
    return serializar_colaborador(c)


@app.patch("/colaboradores-dados/{colaborador_id}")
def editar_colaborador(
    colaborador_id: int,
    dados: ColaboradorUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    colaborador = db.get(Colaborador, colaborador_id)
    if colaborador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador nao encontrado")

    campos = dados.model_dump(exclude_unset=True)

    if "empresa_id" in campos:
        if db.get(Empresa, campos["empresa_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa invalida")
        colaborador.empresa_id = campos["empresa_id"]
    if "nome" in campos:
        nome = (campos["nome"] or "").strip()
        if not nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome nao pode ficar vazio")
        colaborador.nome = nome
    if "registro" in campos:
        colaborador.registro = campos["registro"].strip() if campos["registro"] else None
    if "cargo" in campos:
        colaborador.cargo = campos["cargo"].strip() if campos["cargo"] else None
    if "contato" in campos:
        colaborador.contato = campos["contato"].strip() if campos["contato"] else None
    if "data_admissao" in campos:
        colaborador.data_admissao = date.fromisoformat(campos["data_admissao"]) if campos["data_admissao"] else None
    if "aniversario_dia" in campos or "aniversario_mes" in campos:
        novo_dia = campos.get("aniversario_dia", colaborador.aniversario_dia)
        novo_mes = campos.get("aniversario_mes", colaborador.aniversario_mes)
        _validar_aniversario(novo_dia, novo_mes)
        colaborador.aniversario_dia = novo_dia
        colaborador.aniversario_mes = novo_mes
    if "supervisor_id" in campos:
        if campos["supervisor_id"] is not None and db.get(Usuario, campos["supervisor_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supervisor invalido")
        colaborador.supervisor_id = campos["supervisor_id"]
    if "status" in campos:
        if campos["status"] not in ("ativo", "afastado", "desligado"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status invalido")
        colaborador.status = campos["status"]

    db.commit()
    db.refresh(colaborador)
    return serializar_colaborador(colaborador)


@app.get("/colaboradores-dados/{colaborador_id}/eventos")
def listar_eventos_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    eventos = (
        db.query(ColaboradorEvento)
        .filter(ColaboradorEvento.colaborador_id == colaborador_id)
        .order_by(ColaboradorEvento.criado_em.desc())
        .all()
    )
    return [serializar_evento_colaborador(e) for e in eventos]


@app.post("/colaboradores-dados/{colaborador_id}/eventos", status_code=status.HTTP_201_CREATED)
def criar_evento_colaborador(
    colaborador_id: int,
    tipo: str = Form(...),
    descricao: str | None = Form(None),
    data_inicio: str | None = Form(None),
    data_fim: str | None = Form(None),
    colaborador_relacionado_id: int | None = Form(None),
    arquivo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    colaborador = db.get(Colaborador, colaborador_id)
    if colaborador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador nao encontrado")

    if tipo not in CHAVES_TIPO_EVENTO_VALIDAS or tipo == "cobertura":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de evento invalido")

    if tipo in ("atestado", "falta", "ferias") and not data_inicio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe a data")

    if tipo == "aso" and (not data_inicio or not data_fim):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe a data do exame e a data de vencimento do ASO",
        )

    data_inicio_obj = date.fromisoformat(data_inicio) if data_inicio else None
    data_fim_obj = date.fromisoformat(data_fim) if data_fim else None

    relacionado = None
    if colaborador_relacionado_id is not None:
        relacionado = db.get(Colaborador, colaborador_relacionado_id)
        if relacionado is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador relacionado invalido")

    arquivo_path_salvo = None
    arquivo_nome_original = None
    if arquivo is not None and arquivo.filename:
        extensao = Path(arquivo.filename).suffix.lower()
        if extensao not in EXTENSOES_PERMITIDAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser JPEG, PNG ou PDF"
            )
        conteudo = arquivo.file.read()
        if len(conteudo) > TAMANHO_MAXIMO_ARQUIVO:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo maior que 10MB")

        pasta_colaborador = PASTA_UPLOADS / str(colaborador_id)
        pasta_colaborador.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
        caminho_completo = pasta_colaborador / nome_arquivo
        caminho_completo.write_bytes(conteudo)
        arquivo_path_salvo = str(caminho_completo)
        arquivo_nome_original = arquivo.filename

    evento = ColaboradorEvento(
        colaborador_id=colaborador_id,
        tipo=tipo,
        descricao=descricao.strip() if descricao else None,
        data_inicio=data_inicio_obj,
        data_fim=data_fim_obj,
        colaborador_relacionado_id=colaborador_relacionado_id,
        arquivo_path=arquivo_path_salvo,
        arquivo_nome_original=arquivo_nome_original,
        registrado_por_id=usuario.id,
    )
    db.add(evento)

    # Falta com indicacao de quem cobriu: registra o par tambem no substituto.
    if tipo == "falta" and relacionado is not None:
        evento_cobertura = ColaboradorEvento(
            colaborador_id=relacionado.id,
            tipo="cobertura",
            descricao=f"Cobriu a falta de {colaborador.nome}",
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            colaborador_relacionado_id=colaborador_id,
            registrado_por_id=usuario.id,
        )
        db.add(evento_cobertura)

    db.commit()
    db.refresh(evento)
    return serializar_evento_colaborador(evento)


@app.get("/colaboradores-dados/eventos/{evento_id}/arquivo")
def baixar_arquivo_evento(
    evento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    evento = db.get(ColaboradorEvento, evento_id)
    if evento is None or not evento.arquivo_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo nao encontrado")
    return FileResponse(evento.arquivo_path, filename=evento.arquivo_nome_original or "documento")


@app.patch("/colaboradores-dados/eventos/{evento_id}")
def editar_evento_colaborador(
    evento_id: int,
    dados: ColaboradorEventoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    evento = db.get(ColaboradorEvento, evento_id)
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro nao encontrado")

    campos = dados.model_dump(exclude_unset=True)

    if "descricao" in campos:
        evento.descricao = campos["descricao"].strip() if campos["descricao"] else None
    if "data_inicio" in campos:
        evento.data_inicio = date.fromisoformat(campos["data_inicio"]) if campos["data_inicio"] else None
    if "data_fim" in campos:
        evento.data_fim = date.fromisoformat(campos["data_fim"]) if campos["data_fim"] else None

    db.commit()
    db.refresh(evento)
    return serializar_evento_colaborador(evento)


@app.delete("/colaboradores-dados/eventos/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_evento_colaborador(
    evento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    evento = db.get(ColaboradorEvento, evento_id)
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro nao encontrado")

    if evento.arquivo_path and os.path.exists(evento.arquivo_path):
        os.remove(evento.arquivo_path)

    db.delete(evento)
    db.commit()


DIAS_SEMANA_ORDEM = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
DIAS_SEMANA_LABEL = {
    "segunda": "Segunda", "terca": "Terça", "quarta": "Quarta", "quinta": "Quinta",
    "sexta": "Sexta", "sabado": "Sábado", "domingo": "Domingo",
}


def serializar_horario(h: HorarioServico) -> dict:
    return {
        "id": h.id,
        "colaborador_id": h.colaborador_id,
        "colaborador_nome": h.colaborador.nome,
        "cliente_id": h.cliente_id,
        "cliente_nome": h.cliente.nome,
        "dia_semana": h.dia_semana,
        "dia_semana_label": DIAS_SEMANA_LABEL.get(h.dia_semana, h.dia_semana),
        "turno": h.turno,
        "hora_inicio": h.hora_inicio,
        "hora_fim": h.hora_fim,
    }


@app.get("/colaboradores-dados/{colaborador_id}/horarios")
def horarios_do_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    registros = (
        db.query(HorarioServico)
        .filter(HorarioServico.colaborador_id == colaborador_id)
        .all()
    )
    registros.sort(key=lambda h: (DIAS_SEMANA_ORDEM.index(h.dia_semana), h.turno))
    return [serializar_horario(h) for h in registros]


@app.get("/clientes-dados/{cliente_id}/horarios")
def horarios_do_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    registros = (
        db.query(HorarioServico)
        .filter(HorarioServico.cliente_id == cliente_id)
        .all()
    )
    registros.sort(key=lambda h: (DIAS_SEMANA_ORDEM.index(h.dia_semana), h.turno))
    return [serializar_horario(h) for h in registros]


TURNOS_VALIDOS = {"manha", "tarde", "noite"}


def _checar_conflito_horario(
    db: Session, colaborador_id: int, dia_semana: str, turno: str, ignorar_id: int | None = None
) -> None:
    """Um colaborador nao pode estar em dois lugares no mesmo dia/turno."""
    query = db.query(HorarioServico).filter(
        HorarioServico.colaborador_id == colaborador_id,
        HorarioServico.dia_semana == dia_semana,
        HorarioServico.turno == turno,
    )
    if ignorar_id is not None:
        query = query.filter(HorarioServico.id != ignorar_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse colaborador ja tem um horario nesse dia/turno. Edite o horario existente em vez de criar um novo.",
        )


@app.post("/horarios-servico", status_code=status.HTTP_201_CREATED)
def criar_horario(
    dados: HorarioServicoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if dados.dia_semana not in DIAS_SEMANA_ORDEM:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dia da semana invalido")
    if dados.turno not in TURNOS_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Turno invalido")
    if db.get(Colaborador, dados.colaborador_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador invalido")
    if db.get(Cliente, dados.cliente_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente invalido")

    _checar_conflito_horario(db, dados.colaborador_id, dados.dia_semana, dados.turno)

    horario = HorarioServico(
        colaborador_id=dados.colaborador_id,
        cliente_id=dados.cliente_id,
        dia_semana=dados.dia_semana,
        turno=dados.turno,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
    )
    db.add(horario)
    db.commit()
    db.refresh(horario)
    return serializar_horario(horario)


@app.patch("/horarios-servico/{horario_id}")
def editar_horario(
    horario_id: int,
    dados: HorarioServicoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    horario = db.get(HorarioServico, horario_id)
    if horario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Horario nao encontrado")

    campos = dados.model_dump(exclude_unset=True)

    novo_colaborador_id = campos.get("colaborador_id", horario.colaborador_id)
    novo_dia = campos.get("dia_semana", horario.dia_semana)
    novo_turno = campos.get("turno", horario.turno)

    if "colaborador_id" in campos or "dia_semana" in campos or "turno" in campos:
        if novo_dia not in DIAS_SEMANA_ORDEM:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dia da semana invalido")
        if novo_turno not in TURNOS_VALIDOS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Turno invalido")
        _checar_conflito_horario(db, novo_colaborador_id, novo_dia, novo_turno, ignorar_id=horario_id)

    if "colaborador_id" in campos:
        if db.get(Colaborador, campos["colaborador_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador invalido")
        horario.colaborador_id = campos["colaborador_id"]
    if "cliente_id" in campos:
        if db.get(Cliente, campos["cliente_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente invalido")
        horario.cliente_id = campos["cliente_id"]
    if "dia_semana" in campos:
        horario.dia_semana = campos["dia_semana"]
    if "turno" in campos:
        horario.turno = campos["turno"]
    if "hora_inicio" in campos:
        horario.hora_inicio = campos["hora_inicio"]
    if "hora_fim" in campos:
        horario.hora_fim = campos["hora_fim"]

    db.commit()
    db.refresh(horario)
    return serializar_horario(horario)


@app.delete("/horarios-servico/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_horario(
    horario_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    horario = db.get(HorarioServico, horario_id)
    if horario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Horario nao encontrado")
    db.delete(horario)
    db.commit()


@app.get("/usuarios-dados")
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("usuarios")),
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


@app.delete("/avisos-dados/{aviso_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_aviso(
    aviso_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    aviso = db.get(Aviso, aviso_id)
    if aviso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aviso nao encontrado")

    if aviso.criado_por_id != usuario.id and usuario.papel != "escritorio":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce so pode excluir avisos que voce mesmo criou",
        )

    db.delete(aviso)
    db.commit()


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


@app.get("/asos-dados")
def listar_asos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("asos")),
):
    """Painel de controle de ASOs - o ASO mais recente de cada colaborador ativo, com status de vencimento."""
    subquery = (
        db.query(
            ColaboradorEvento.colaborador_id,
            func.max(ColaboradorEvento.data_fim).label("data_fim_max"),
        )
        .filter(ColaboradorEvento.tipo == "aso", ColaboradorEvento.data_fim.isnot(None))
        .group_by(ColaboradorEvento.colaborador_id)
        .subquery()
    )

    eventos = (
        db.query(ColaboradorEvento)
        .join(
            subquery,
            (ColaboradorEvento.colaborador_id == subquery.c.colaborador_id)
            & (ColaboradorEvento.data_fim == subquery.c.data_fim_max),
        )
        .filter(ColaboradorEvento.tipo == "aso")
        .all()
    )

    hoje = date.today()
    resultado = []
    for e in eventos:
        colaborador = db.get(Colaborador, e.colaborador_id)
        if colaborador is None or colaborador.status == "desligado":
            continue
        dias_restantes = (e.data_fim - hoje).days
        if dias_restantes < 0:
            situacao = "vencido"
        elif dias_restantes <= 7:
            situacao = "proximo"
        else:
            situacao = "ok"
        resultado.append(
            {
                "evento_id": e.id,
                "colaborador_id": colaborador.id,
                "colaborador_nome": colaborador.nome,
                "cargo": colaborador.cargo,
                "empresa_nome": colaborador.empresa.nome,
                "data_exame": e.data_inicio.isoformat() if e.data_inicio else None,
                "data_vencimento": e.data_fim.isoformat() if e.data_fim else None,
                "dias_restantes": dias_restantes,
                "situacao": situacao,
            }
        )

    resultado.sort(key=lambda x: x["dias_restantes"])
    return resultado


@app.post("/asos-dados/testar-email")
def testar_email_aso(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("asos")),
):
    """Dispara a checagem de ASOs e o envio do e-mail na hora, para teste."""
    try:
        resultado = verificar_e_enviar_alertas(db)
        return resultado
    except RuntimeError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


# ---------------------------------------------------------------------------
# Veiculos e manutencao
# ---------------------------------------------------------------------------

# Plano de manutencao de REFERENCIA para o Fiat Mobi 1.0, baseado em fontes
# publicas (nao e' o manual oficial do veiculo - sempre vale mais a cadencia
# oficial de 10.000 km / 12 meses prevista no manual do proprietario).
PLANO_MANUTENCAO_FIAT_MOBI = [
    {"item": "Troca de óleo do motor + filtro de óleo", "intervalo_km": 7500, "critico": False},
    {"item": "Filtro de cabine (ar-condicionado)", "intervalo_km": 15000, "critico": False},
    {"item": "Filtro de ar do motor", "intervalo_km": 20000, "critico": False},
    {"item": "Velas de ignição", "intervalo_km": 25000, "critico": False},
    {"item": "Fluido de freio", "intervalo_km": 24000, "critico": False},
    {"item": "Pastilhas de freio (verificar desgaste)", "intervalo_km": 30000, "critico": False},
    {"item": "Filtro de combustível", "intervalo_km": 30000, "critico": False},
    {"item": "Óleo do câmbio manual", "intervalo_km": 80000, "critico": False},
    {"item": "Correia dentada (crítico)", "intervalo_km": 60000, "critico": True},
]


def _calcular_plano_sugerido(km_atual: int, baseline_km: int = 0) -> list[dict]:
    """
    Calcula o proximo ponto de manutencao de cada item, a partir de uma
    base conhecida (o km da ultima manutencao PREVENTIVA registrada, ou
    0 se nunca houve nenhuma). Isso evita assumir, sem nenhuma evidencia,
    que intervalos anteriores foram cumpridos - se o carro esta em
    32.000 km e nunca teve manutencao registrada, um item com intervalo
    de 7.500 km ja esta vencido, nao "em dia".
    """
    itens = []
    for referencia in PLANO_MANUTENCAO_FIAT_MOBI:
        intervalo = referencia["intervalo_km"]
        proximo_km = baseline_km + intervalo
        km_restantes = proximo_km - km_atual
        margem_aviso = 3000 if referencia["critico"] else 1000
        if km_restantes <= 0:
            situacao = "vencido"
        elif km_restantes <= margem_aviso:
            situacao = "proximo"
        else:
            situacao = "ok"
        itens.append(
            {
                "item": referencia["item"],
                "intervalo_km": intervalo,
                "critico": referencia["critico"],
                "proximo_km": proximo_km,
                "km_restantes": km_restantes,
                "situacao": situacao,
            }
        )
    itens.sort(key=lambda x: x["km_restantes"])
    return itens


def serializar_veiculo(v: Veiculo, db: Session | None = None, incluir_plano: bool = False) -> dict:
    dados = {
        "id": v.id,
        "placa": v.placa,
        "modelo": v.modelo,
        "ano": v.ano,
        "apelido": v.apelido,
        "km_atual": v.km_atual,
        "ativo": v.ativo,
    }
    if incluir_plano:
        baseline_km = 0
        if db is not None:
            ultima_preventiva = (
                db.query(ManutencaoVeiculo)
                .filter_by(veiculo_id=v.id, tipo="preventiva")
                .order_by(ManutencaoVeiculo.km.desc())
                .first()
            )
            if ultima_preventiva is not None:
                baseline_km = ultima_preventiva.km
        dados["plano_sugerido"] = _calcular_plano_sugerido(v.km_atual, baseline_km)
    return dados


def serializar_manutencao(m: ManutencaoVeiculo) -> dict:
    return {
        "id": m.id,
        "veiculo_id": m.veiculo_id,
        "tipo": m.tipo,
        "data": m.data.isoformat(),
        "km": m.km,
        "descricao": m.descricao,
        "custo": m.custo,
        "registrado_por": m.registrado_por.nome,
        "criado_em": m.criado_em.isoformat(),
    }


@app.get("/veiculos-dados")
def listar_veiculos(
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    query = db.query(Veiculo)
    if not incluir_inativos:
        query = query.filter(Veiculo.ativo.is_(True))
    veiculos = query.order_by(Veiculo.placa).all()
    return [serializar_veiculo(v) for v in veiculos]


@app.post("/veiculos-dados", status_code=status.HTTP_201_CREATED)
def criar_veiculo(
    dados: VeiculoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    placa = dados.placa.strip().upper()
    if not placa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe a placa")
    if db.query(Veiculo).filter_by(placa=placa).first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um veículo com essa placa")

    veiculo = Veiculo(
        placa=placa,
        modelo=dados.modelo.strip(),
        ano=dados.ano,
        apelido=dados.apelido.strip() if dados.apelido else None,
        km_atual=dados.km_atual,
    )
    db.add(veiculo)
    db.commit()
    db.refresh(veiculo)
    return serializar_veiculo(veiculo)


@app.get("/veiculos-dados/{veiculo_id}")
def detalhe_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    veiculo = db.get(Veiculo, veiculo_id)
    if veiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")
    return serializar_veiculo(veiculo, db=db, incluir_plano=True)


@app.patch("/veiculos-dados/{veiculo_id}")
def editar_veiculo(
    veiculo_id: int,
    dados: VeiculoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    veiculo = db.get(Veiculo, veiculo_id)
    if veiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    campos = dados.model_dump(exclude_unset=True)

    if "placa" in campos:
        nova_placa = (campos["placa"] or "").strip().upper()
        if not nova_placa:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Placa não pode ficar vazia")
        conflito = db.query(Veiculo).filter(Veiculo.placa == nova_placa, Veiculo.id != veiculo_id).first()
        if conflito is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um veículo com essa placa")
        veiculo.placa = nova_placa
    if "modelo" in campos:
        veiculo.modelo = campos["modelo"].strip() if campos["modelo"] else veiculo.modelo
    if "ano" in campos:
        veiculo.ano = campos["ano"]
    if "apelido" in campos:
        veiculo.apelido = campos["apelido"].strip() if campos["apelido"] else None
    if "km_atual" in campos:
        if campos["km_atual"] is not None and campos["km_atual"] < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quilometragem não pode ser negativa")
        veiculo.km_atual = campos["km_atual"]
    if "ativo" in campos:
        veiculo.ativo = campos["ativo"]

    db.commit()
    db.refresh(veiculo)
    return serializar_veiculo(veiculo, db=db, incluir_plano=True)


@app.delete("/veiculos-dados/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    veiculo = db.get(Veiculo, veiculo_id)
    if veiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")
    db.delete(veiculo)
    db.commit()


@app.get("/veiculos-dados/{veiculo_id}/manutencoes")
def listar_manutencoes(
    veiculo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    manutencoes = (
        db.query(ManutencaoVeiculo)
        .filter(ManutencaoVeiculo.veiculo_id == veiculo_id)
        .order_by(ManutencaoVeiculo.data.desc())
        .all()
    )
    return [serializar_manutencao(m) for m in manutencoes]


@app.post("/veiculos-dados/{veiculo_id}/manutencoes", status_code=status.HTTP_201_CREATED)
def criar_manutencao(
    veiculo_id: int,
    dados: ManutencaoVeiculoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    veiculo = db.get(Veiculo, veiculo_id)
    if veiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    if dados.tipo not in ("preventiva", "corretiva"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo deve ser preventiva ou corretiva")

    descricao = dados.descricao.strip()
    if not descricao:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Descreva a manutenção realizada")

    manutencao = ManutencaoVeiculo(
        veiculo_id=veiculo_id,
        tipo=dados.tipo,
        data=date.fromisoformat(dados.data),
        km=dados.km,
        descricao=descricao,
        custo=dados.custo,
        registrado_por_id=usuario.id,
    )
    db.add(manutencao)

    # atualiza o km do veiculo se a manutencao registrada for mais recente (km maior)
    if dados.km > veiculo.km_atual:
        veiculo.km_atual = dados.km

    db.commit()
    db.refresh(manutencao)
    return serializar_manutencao(manutencao)


@app.patch("/veiculos-dados/manutencoes/{manutencao_id}")
def editar_manutencao(
    manutencao_id: int,
    dados: ManutencaoVeiculoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    manutencao = db.get(ManutencaoVeiculo, manutencao_id)
    if manutencao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro não encontrado")

    campos = dados.model_dump(exclude_unset=True)

    if "tipo" in campos:
        if campos["tipo"] not in ("preventiva", "corretiva"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo deve ser preventiva ou corretiva")
        manutencao.tipo = campos["tipo"]
    if "data" in campos:
        manutencao.data = date.fromisoformat(campos["data"])
    if "km" in campos:
        manutencao.km = campos["km"]
    if "descricao" in campos:
        descricao = (campos["descricao"] or "").strip()
        if not descricao:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Descrição não pode ficar vazia")
        manutencao.descricao = descricao
    if "custo" in campos:
        manutencao.custo = campos["custo"]

    db.commit()
    db.refresh(manutencao)
    return serializar_manutencao(manutencao)


@app.delete("/veiculos-dados/manutencoes/{manutencao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_manutencao(
    manutencao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("veiculos")),
):
    manutencao = db.get(ManutencaoVeiculo, manutencao_id)
    if manutencao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro não encontrado")
    db.delete(manutencao)
    db.commit()


# ---------------------------------------------------------------------------
# Administracao de permissoes (so super_admin: Caroline e Sidnei)
# ---------------------------------------------------------------------------

@app.get("/admin/permissoes")
def listar_permissoes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_super_admin),
):
    usuarios = db.query(Usuario).filter_by(ativo=True).order_by(Usuario.nome).all()
    overrides = {(o.usuario_id, o.modulo): o.habilitado for o in db.query(UsuarioPermissao).all()}

    linhas = []
    for u in usuarios:
        permissoes = {}
        for modulo_info in MODULOS_PERMISSAO:
            chave = modulo_info["chave"]
            tem_override = (u.id, chave) in overrides
            efetivo = tem_permissao(db, u, chave)
            permissoes[chave] = {"efetivo": efetivo, "tem_override": tem_override}
        linhas.append(
            {
                "usuario_id": u.id,
                "nome": u.nome,
                "papel": u.papel,
                "super_admin": u.super_admin,
                "permissoes": permissoes,
            }
        )

    return {"modulos": MODULOS_PERMISSAO, "usuarios": linhas}


@app.put("/admin/permissoes/{usuario_id}/{modulo}")
def definir_permissao(
    usuario_id: int,
    modulo: str,
    dados: PermissaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_super_admin),
):
    if modulo not in CHAVES_MODULOS_VALIDAS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modulo invalido")

    alvo = db.get(Usuario, usuario_id)
    if alvo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    habilitado = dados.habilitado

    override = db.query(UsuarioPermissao).filter_by(usuario_id=usuario_id, modulo=modulo).first()
    if override is None:
        override = UsuarioPermissao(
            usuario_id=usuario_id, modulo=modulo, habilitado=habilitado, atualizado_por_id=usuario.id
        )
        db.add(override)
    else:
        override.habilitado = habilitado
        override.atualizado_por_id = usuario.id

    db.commit()
    return {"usuario_id": usuario_id, "modulo": modulo, "habilitado": habilitado}


@app.delete("/admin/permissoes/{usuario_id}/{modulo}")
def resetar_permissao(
    usuario_id: int,
    modulo: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_super_admin),
):
    """Remove o override, voltando o usuario para a regra padrao do modulo."""
    override = db.query(UsuarioPermissao).filter_by(usuario_id=usuario_id, modulo=modulo).first()
    if override is not None:
        db.delete(override)
        db.commit()
    return {"usuario_id": usuario_id, "modulo": modulo, "resetado": True}



