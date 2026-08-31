import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

import jwt
from alertas_aso import verificar_e_enviar_alertas
from alertas_custos import verificar_e_enviar_custos
from alertas_experiencia import verificar_e_enviar_experiencias
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal, get_db
from models import (
    Aviso,
    Chamado,
    Cliente,
    Colaborador,
    ColaboradorEvento,
    CustoDiario,
    Empresa,
    EstoqueItem,
    EstoqueMovimento,
    HistoricoMapaServico,
    HorarioServico,
    ManutencaoVeiculo,
    MetlifeLancamento,
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
    CustoDiarioUpdate,
    EstoqueItemCreate,
    EstoqueItemUpdate,
    EstoqueMovimentoCreate,
    HorarioServicoCreate,
    HorarioServicoUpdate,
    LoginRequest,
    ManutencaoVeiculoCreate,
    ManutencaoVeiculoUpdate,
    MetlifeLancamentoCreate,
    MetlifeLancamentoUpdate,
    PermissaoUpdate,
    TokenResponse,
    UsuarioAcessoUpdate,
    UsuarioCreate,
    VeiculoCreate,
    VeiculoUpdate,
)
from security import criar_token, decodificar_token, hash_senha, verificar_senha

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


def job_verificar_custos():
    """Roda em background, uma vez por dia no fim do expediente."""
    db = SessionLocal()
    try:
        resultado = verificar_e_enviar_custos(db)
        print("[custos-diarios]", resultado)
    except Exception as erro:
        print("[custos-diarios] erro ao verificar/enviar:", erro)
    finally:
        db.close()


def job_verificar_experiencias():
    """Roda em background, uma vez por dia - checa checkpoints de 30/90 dias."""
    db = SessionLocal()
    try:
        resultado = verificar_e_enviar_experiencias(db)
        print("[experiencia]", resultado)
    except Exception as erro:
        print("[experiencia] erro ao verificar/enviar:", erro)
    finally:
        db.close()


agendador = BackgroundScheduler()
agendador.add_job(job_verificar_asos, "cron", hour=8, minute=0)
agendador.add_job(job_verificar_custos, "cron", hour=19, minute=0)
agendador.add_job(job_verificar_experiencias, "cron", hour=8, minute=10)
agendador.start()

PASTA_UPLOADS = Path("uploads/colaboradores")
PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)

PASTA_UPLOADS_CUSTOS = Path("uploads/custos_diarios")
PASTA_UPLOADS_CUSTOS.mkdir(parents=True, exist_ok=True)

EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".pdf"}
TAMANHO_MAXIMO_ARQUIVO = 10 * 1024 * 1024  # 10 MB

TIPOS_CUSTO_DIARIO = [
    {"chave": "combustivel", "label": "Combustível"},
    {"chave": "estacionamento", "label": "Estacionamento"},
    {"chave": "pedagio", "label": "Pedágio"},
    {"chave": "alimentacao", "label": "Alimentação"},
    {"chave": "diaria", "label": "Diária"},
    {"chave": "outros", "label": "Outros"},
]
CHAVES_TIPO_CUSTO_VALIDAS = {t["chave"] for t in TIPOS_CUSTO_DIARIO}

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
    {"chave": "relatorios", "label": "Relatórios gerenciais", "padrao_escritorio_apenas": True},
    {"chave": "estoque", "label": "Controle de Estoque", "padrao_escritorio_apenas": True},
    {"chave": "mapa_servico", "label": "Histórico do Mapa de Serviço", "padrao_escritorio_apenas": True},
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


@app.get("/custos-diarios", include_in_schema=False)
def pagina_custos_diarios():
    return FileResponse("static/custos-diarios.html")


@app.get("/relatorios", include_in_schema=False)
def pagina_relatorios():
    return FileResponse("static/relatorios.html")


@app.get("/estoque", include_in_schema=False)
def pagina_estoque():
    return FileResponse("static/estoque.html")


@app.get("/mapa-servico", include_in_schema=False)
def pagina_mapa_servico():
    return FileResponse("static/mapa-servico.html")


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
        "supervisor_id": c.supervisor_id,
        "supervisor_nome": c.supervisor.nome if c.supervisor else None,
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

    if dados.supervisor_id is not None and db.get(Usuario, dados.supervisor_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supervisor invalido")

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
        supervisor_id=dados.supervisor_id,
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
    if "supervisor_id" in campos:
        if campos["supervisor_id"] is not None and db.get(Usuario, campos["supervisor_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supervisor invalido")
        cliente.supervisor_id = campos["supervisor_id"]
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
        "data_fim_experiencia_30": c.data_fim_experiencia_30.isoformat() if c.data_fim_experiencia_30 else None,
        "data_fim_experiencia_90": c.data_fim_experiencia_90.isoformat() if c.data_fim_experiencia_90 else None,
        "vt_numero_cartao": c.vt_numero_cartao,
        "vt_situacao": c.vt_situacao,
        "vt_saldo": c.vt_saldo,
        "seguro_vida_data_inclusao": c.seguro_vida_data_inclusao.isoformat() if c.seguro_vida_data_inclusao else None,
        "seguro_vida_data_exclusao": c.seguro_vida_data_exclusao.isoformat() if c.seguro_vida_data_exclusao else None,
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

    fim_experiencia_30 = admissao + timedelta(days=29) if admissao else None
    fim_experiencia_90 = admissao + timedelta(days=89) if admissao else None

    colaborador = Colaborador(
        empresa_id=dados.empresa_id,
        registro=dados.registro.strip() if dados.registro else None,
        nome=nome,
        cargo=dados.cargo.strip() if dados.cargo else None,
        contato=dados.contato.strip() if dados.contato else None,
        data_admissao=admissao,
        data_fim_experiencia_30=fim_experiencia_30,
        data_fim_experiencia_90=fim_experiencia_90,
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
    if "data_fim_experiencia_30" in campos:
        valor = campos["data_fim_experiencia_30"]
        colaborador.data_fim_experiencia_30 = date.fromisoformat(valor) if valor else None
    if "data_fim_experiencia_90" in campos:
        valor = campos["data_fim_experiencia_90"]
        colaborador.data_fim_experiencia_90 = date.fromisoformat(valor) if valor else None
    if "vt_numero_cartao" in campos:
        colaborador.vt_numero_cartao = campos["vt_numero_cartao"].strip() if campos["vt_numero_cartao"] else None
    if "vt_situacao" in campos:
        colaborador.vt_situacao = campos["vt_situacao"].strip() if campos["vt_situacao"] else None
    if "vt_saldo" in campos:
        colaborador.vt_saldo = campos["vt_saldo"]
    if "seguro_vida_data_inclusao" in campos:
        valor = campos["seguro_vida_data_inclusao"]
        colaborador.seguro_vida_data_inclusao = date.fromisoformat(valor) if valor else None
    if "seguro_vida_data_exclusao" in campos:
        valor = campos["seguro_vida_data_exclusao"]
        colaborador.seguro_vida_data_exclusao = date.fromisoformat(valor) if valor else None
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
        "data_inicio": h.data_inicio.isoformat() if h.data_inicio else None,
        "data_fim": h.data_fim.isoformat() if h.data_fim else None,
    }


@app.get("/colaboradores-dados/{colaborador_id}/horarios")
def horarios_do_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    registros = (
        db.query(HorarioServico)
        .filter(HorarioServico.colaborador_id == colaborador_id, HorarioServico.data_fim.is_(None))
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
        .filter(HorarioServico.cliente_id == cliente_id, HorarioServico.data_fim.is_(None))
        .all()
    )
    registros.sort(key=lambda h: (DIAS_SEMANA_ORDEM.index(h.dia_semana), h.turno))
    return [serializar_horario(h) for h in registros]


TURNOS_VALIDOS = {"manha", "tarde", "noite"}


def _horarios_se_sobrepoem(inicio1: str, fim1: str, inicio2: str, fim2: str) -> bool:
    """Compara strings HH:MM - a comparacao lexicografica funciona pois o formato e sempre zero-padded."""
    return inicio1 < fim2 and inicio2 < fim1


def _checar_conflito_horario(
    db: Session,
    colaborador_id: int,
    dia_semana: str,
    hora_inicio: str,
    hora_fim: str,
    ignorar_id: int | None = None,
) -> None:
    """
    Um colaborador nao pode estar em dois lugares ao mesmo tempo. So
    bloqueia se as faixas de horario realmente se sobrepoem - o mesmo
    dia com turnos iguais mas horarios diferentes (ex: 06:00-08:00 e
    08:30-12:00) e permitido.
    """
    query = db.query(HorarioServico).filter(
        HorarioServico.colaborador_id == colaborador_id,
        HorarioServico.dia_semana == dia_semana,
        HorarioServico.data_fim.is_(None),
    )
    if ignorar_id is not None:
        query = query.filter(HorarioServico.id != ignorar_id)

    for existente in query.all():
        if _horarios_se_sobrepoem(hora_inicio, hora_fim, existente.hora_inicio, existente.hora_fim):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Esse colaborador ja tem um horario que se sobrepoe nesse dia "
                    f"({existente.hora_inicio}-{existente.hora_fim}). Ajuste o horario para nao coincidir."
                ),
            )


def _registrar_evento_mapa_servico(
    db: Session,
    horario: HorarioServico,
    tipo_evento: str,
    registrado_por_id: int,
    motivo: str | None = None,
) -> None:
    db.add(
        HistoricoMapaServico(
            horario_servico_id=horario.id,
            colaborador_id=horario.colaborador_id,
            cliente_id=horario.cliente_id,
            tipo_evento=tipo_evento,
            dia_semana=horario.dia_semana,
            turno=horario.turno,
            hora_inicio=horario.hora_inicio,
            hora_fim=horario.hora_fim,
            motivo=motivo,
            registrado_por_id=registrado_por_id,
        )
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
    if dados.hora_inicio >= dados.hora_fim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A hora final deve ser depois da hora inicial")

    _checar_conflito_horario(db, dados.colaborador_id, dados.dia_semana, dados.hora_inicio, dados.hora_fim)

    horario = HorarioServico(
        colaborador_id=dados.colaborador_id,
        cliente_id=dados.cliente_id,
        dia_semana=dados.dia_semana,
        turno=dados.turno,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
        data_inicio=date.today(),
    )
    db.add(horario)
    db.flush()
    _registrar_evento_mapa_servico(db, horario, "iniciado", usuario.id)
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
    nova_hora_inicio = campos.get("hora_inicio", horario.hora_inicio)
    nova_hora_fim = campos.get("hora_fim", horario.hora_fim)

    if novo_dia not in DIAS_SEMANA_ORDEM:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dia da semana invalido")
    if novo_turno not in TURNOS_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Turno invalido")
    if nova_hora_inicio >= nova_hora_fim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A hora final deve ser depois da hora inicial")

    if "cliente_id" in campos and campos["cliente_id"] != horario.cliente_id:
        # Trocar de cliente = encerrar o vinculo atual e abrir um novo, para manter o historico limpo
        if db.get(Cliente, campos["cliente_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente invalido")

        _checar_conflito_horario(db, novo_colaborador_id, novo_dia, nova_hora_inicio, nova_hora_fim, ignorar_id=horario_id)

        horario.data_fim = date.today()
        _registrar_evento_mapa_servico(db, horario, "encerrado", usuario.id, motivo="Mudou de cliente")

        novo_horario = HorarioServico(
            colaborador_id=novo_colaborador_id,
            cliente_id=campos["cliente_id"],
            dia_semana=novo_dia,
            turno=novo_turno,
            hora_inicio=nova_hora_inicio,
            hora_fim=nova_hora_fim,
            data_inicio=date.today(),
        )
        db.add(novo_horario)
        db.flush()
        _registrar_evento_mapa_servico(db, novo_horario, "iniciado", usuario.id, motivo="Mudou de cliente")
        db.commit()
        db.refresh(novo_horario)
        return serializar_horario(novo_horario)

    if (
        "colaborador_id" in campos
        or "dia_semana" in campos
        or "hora_inicio" in campos
        or "hora_fim" in campos
    ):
        _checar_conflito_horario(db, novo_colaborador_id, novo_dia, nova_hora_inicio, nova_hora_fim, ignorar_id=horario_id)

    if "colaborador_id" in campos:
        if db.get(Colaborador, campos["colaborador_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador invalido")
        horario.colaborador_id = campos["colaborador_id"]
    if "dia_semana" in campos:
        horario.dia_semana = campos["dia_semana"]
    if "turno" in campos:
        horario.turno = campos["turno"]
    if "hora_inicio" in campos:
        horario.hora_inicio = campos["hora_inicio"]
    if "hora_fim" in campos:
        horario.hora_fim = campos["hora_fim"]

    db.flush()
    _registrar_evento_mapa_servico(db, horario, "editado", usuario.id)
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
    if horario.data_fim is not None:
        return
    horario.data_fim = date.today()
    _registrar_evento_mapa_servico(db, horario, "encerrado", usuario.id)
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


@app.post("/usuarios-dados", status_code=status.HTTP_201_CREATED)
def criar_usuario_endpoint(
    dados: UsuarioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("usuarios")),
):
    nome = dados.nome.strip()
    email = dados.email.strip().lower()
    if not nome or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe nome e e-mail")
    if dados.papel not in ("escritorio", "supervisor"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Papel deve ser escritorio ou supervisor")
    if len(dados.senha) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A senha deve ter pelo menos 4 caracteres")
    if db.query(Usuario).filter_by(email=email).first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário com esse e-mail")

    novo_usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=hash_senha(dados.senha),
        papel=dados.papel,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"id": novo_usuario.id, "nome": novo_usuario.nome, "email": novo_usuario.email, "papel": novo_usuario.papel, "ativo": novo_usuario.ativo}


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
                "email": u.email,
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


@app.patch("/admin/usuarios/{usuario_id}/acesso")
def redefinir_acesso_usuario(
    usuario_id: int,
    dados: UsuarioAcessoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_super_admin),
):
    """Redefine o e-mail de login e/ou a senha de um usuario. So super_admin."""
    alvo = db.get(Usuario, usuario_id)
    if alvo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    if not dados.email and not dados.nova_senha:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe um novo e-mail ou uma nova senha")

    if dados.email:
        novo_email = dados.email.strip().lower()
        conflito = db.query(Usuario).filter(Usuario.email == novo_email, Usuario.id != usuario_id).first()
        if conflito is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário com esse e-mail")
        alvo.email = novo_email

    if dados.nova_senha:
        if len(dados.nova_senha) < 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A senha deve ter pelo menos 4 caracteres")
        alvo.senha_hash = hash_senha(dados.nova_senha)

    db.commit()
    return {"id": alvo.id, "email": alvo.email, "senha_alterada": bool(dados.nova_senha)}


# ---------------------------------------------------------------------------
# Relatorio gerencial
# ---------------------------------------------------------------------------

@app.get("/relatorios-dados")
def relatorio_gerencial(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("relatorios")),
):
    hoje = date.today()
    inicio = date.fromisoformat(data_inicio) if data_inicio else date(hoje.year, hoje.month, 1)
    fim = date.fromisoformat(data_fim) if data_fim else hoje

    if inicio > fim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data inicial nao pode ser depois da final")

    filtro_criado = func.date(Chamado.criado_em).between(inicio, fim)
    filtro_finalizado = func.date(Chamado.finalizado_em).between(inicio, fim)

    # ---------- Chamados ----------
    total_abertos = db.query(Chamado).filter(filtro_criado).count()
    total_finalizados = db.query(Chamado).filter(filtro_finalizado).count()

    por_tipo_query = (
        db.query(Chamado.tipo, func.count(Chamado.id))
        .filter(filtro_criado)
        .group_by(Chamado.tipo)
        .order_by(func.count(Chamado.id).desc())
        .all()
    )
    labels_tipo = {t["chave"]: t["label"] for t in TIPOS_CHAMADO}
    chamados_por_tipo = [{"tipo": labels_tipo.get(t, t), "total": n} for t, n in por_tipo_query]

    por_prioridade_query = (
        db.query(Chamado.prioridade, func.count(Chamado.id))
        .filter(filtro_criado)
        .group_by(Chamado.prioridade)
        .all()
    )
    labels_prioridade = {p["chave"]: p["label"] for p in PRIORIDADES_CHAMADO}
    chamados_por_prioridade = [
        {"prioridade": labels_prioridade.get(p, p), "total": n} for p, n in por_prioridade_query
    ]

    tempo_medio_query = (
        db.query(func.avg(func.extract("epoch", Chamado.finalizado_em - Chamado.criado_em)))
        .filter(filtro_finalizado)
        .scalar()
    )
    tempo_medio_horas = round(tempo_medio_query / 3600, 1) if tempo_medio_query else None

    top_clientes_query = (
        db.query(Cliente.nome, func.count(Chamado.id).label("total"))
        .join(Chamado, Chamado.cliente_id == Cliente.id)
        .filter(filtro_criado)
        .group_by(Cliente.nome)
        .order_by(func.count(Chamado.id).desc())
        .limit(5)
        .all()
    )
    top_clientes = [{"cliente": nome, "total": total} for nome, total in top_clientes_query]

    top_supervisores_query = (
        db.query(Usuario.nome, func.count(Chamado.id).label("total"))
        .join(Chamado, Chamado.responsavel_id == Usuario.id)
        .filter(filtro_finalizado)
        .group_by(Usuario.nome)
        .order_by(func.count(Chamado.id).desc())
        .limit(5)
        .all()
    )
    top_supervisores = [{"supervisor": nome, "total": total} for nome, total in top_supervisores_query]

    # ---------- Colaboradores ----------
    total_colaboradores_ativos = db.query(Colaborador).filter(Colaborador.status != "desligado").count()
    admissoes_periodo = (
        db.query(Colaborador).filter(Colaborador.data_admissao.between(inicio, fim)).count()
    )
    faltas_periodo = (
        db.query(ColaboradorEvento)
        .filter(ColaboradorEvento.tipo == "falta", ColaboradorEvento.data_inicio.between(inicio, fim))
        .count()
    )
    advertencias_periodo = (
        db.query(ColaboradorEvento)
        .filter(ColaboradorEvento.tipo == "advertencia", func.date(ColaboradorEvento.criado_em).between(inicio, fim))
        .count()
    )

    hoje_real = date.today()
    subquery_aso = (
        db.query(
            ColaboradorEvento.colaborador_id,
            func.max(ColaboradorEvento.data_fim).label("data_fim_max"),
        )
        .filter(ColaboradorEvento.tipo == "aso", ColaboradorEvento.data_fim.isnot(None))
        .group_by(ColaboradorEvento.colaborador_id)
        .subquery()
    )
    asos_vencidos_atual = (
        db.query(ColaboradorEvento)
        .join(
            subquery_aso,
            (ColaboradorEvento.colaborador_id == subquery_aso.c.colaborador_id)
            & (ColaboradorEvento.data_fim == subquery_aso.c.data_fim_max),
        )
        .filter(ColaboradorEvento.tipo == "aso", ColaboradorEvento.data_fim < hoje_real)
        .count()
    )

    # ---------- Veiculos ----------
    manutencoes_periodo_query = (
        db.query(ManutencaoVeiculo.tipo, func.count(ManutencaoVeiculo.id), func.sum(ManutencaoVeiculo.custo))
        .filter(ManutencaoVeiculo.data.between(inicio, fim))
        .group_by(ManutencaoVeiculo.tipo)
        .all()
    )
    manutencoes_por_tipo = [
        {"tipo": "Preventiva" if t == "preventiva" else "Corretiva", "total": n, "custo": float(c) if c else 0.0}
        for t, n, c in manutencoes_periodo_query
    ]
    custo_total_periodo = sum(m["custo"] for m in manutencoes_por_tipo)

    custo_por_veiculo_query = (
        db.query(Veiculo.placa, Veiculo.apelido, func.count(ManutencaoVeiculo.id), func.sum(ManutencaoVeiculo.custo))
        .join(ManutencaoVeiculo, ManutencaoVeiculo.veiculo_id == Veiculo.id)
        .filter(ManutencaoVeiculo.data.between(inicio, fim))
        .group_by(Veiculo.placa, Veiculo.apelido)
        .all()
    )
    custo_por_veiculo = [
        {
            "veiculo": apelido or placa,
            "total_manutencoes": n,
            "custo": float(c) if c else 0.0,
        }
        for placa, apelido, n, c in custo_por_veiculo_query
    ]

    # ---------- Clientes ----------
    total_clientes_ativos = db.query(Cliente).filter(Cliente.ativo.is_(True)).count()
    novos_clientes_periodo = db.query(Cliente).filter(func.date(Cliente.criado_em).between(inicio, fim)).count()

    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "chamados": {
            "total_abertos": total_abertos,
            "total_finalizados": total_finalizados,
            "tempo_medio_horas": tempo_medio_horas,
            "por_tipo": chamados_por_tipo,
            "por_prioridade": chamados_por_prioridade,
            "top_clientes": top_clientes,
            "top_supervisores": top_supervisores,
        },
        "colaboradores": {
            "total_ativos": total_colaboradores_ativos,
            "admissoes_periodo": admissoes_periodo,
            "faltas_periodo": faltas_periodo,
            "advertencias_periodo": advertencias_periodo,
            "asos_vencidos_atual": asos_vencidos_atual,
        },
        "veiculos": {
            "custo_total_periodo": custo_total_periodo,
            "manutencoes_por_tipo": manutencoes_por_tipo,
            "custo_por_veiculo": custo_por_veiculo,
        },
        "clientes": {
            "total_ativos": total_clientes_ativos,
            "novos_periodo": novos_clientes_periodo,
        },
    }


@app.get("/relatorios-dados/cliente/{cliente_id}")
def relatorio_por_cliente(
    cliente_id: int,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("relatorios")),
):
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    hoje = date.today()
    inicio = date.fromisoformat(data_inicio) if data_inicio else date(hoje.year, hoje.month, 1)
    fim = date.fromisoformat(data_fim) if data_fim else hoje
    if inicio > fim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data inicial nao pode ser depois da final")

    chamados_periodo = (
        db.query(Chamado)
        .filter(Chamado.cliente_id == cliente_id, func.date(Chamado.criado_em).between(inicio, fim))
        .order_by(Chamado.criado_em.desc())
        .all()
    )

    labels_tipo = {t["chave"]: t["label"] for t in TIPOS_CHAMADO}
    labels_prioridade = {p["chave"]: p["label"] for p in PRIORIDADES_CHAMADO}
    labels_status = {s["chave"]: s["label"] for s in STATUS_CHAMADO}

    contagem_tipo: dict[str, int] = {}
    contagem_status: dict[str, int] = {}
    contagem_prioridade: dict[str, int] = {}
    for c in chamados_periodo:
        contagem_tipo[c.tipo] = contagem_tipo.get(c.tipo, 0) + 1
        contagem_status[c.status] = contagem_status.get(c.status, 0) + 1
        contagem_prioridade[c.prioridade] = contagem_prioridade.get(c.prioridade, 0) + 1

    finalizados = [c for c in chamados_periodo if c.status == "finalizado" and c.finalizado_em is not None]
    if finalizados:
        soma_horas = sum((c.finalizado_em - c.criado_em).total_seconds() for c in finalizados) / 3600
        tempo_medio_horas = round(soma_horas / len(finalizados), 1)
    else:
        tempo_medio_horas = None

    horarios = (
        db.query(HorarioServico)
        .filter(HorarioServico.cliente_id == cliente_id, HorarioServico.data_fim.is_(None))
        .all()
    )
    quem_atende = sorted({h.colaborador.nome for h in horarios})

    return {
        "cliente": {"id": cliente.id, "nome": cliente.nome, "empresa_nome": cliente.empresa.nome},
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "total_chamados": len(chamados_periodo),
        "tempo_medio_horas": tempo_medio_horas,
        "por_tipo": [{"tipo": labels_tipo.get(k, k), "total": v} for k, v in contagem_tipo.items()],
        "por_status": [{"status": labels_status.get(k, k), "total": v} for k, v in contagem_status.items()],
        "por_prioridade": [{"prioridade": labels_prioridade.get(k, k), "total": v} for k, v in contagem_prioridade.items()],
        "quem_atende": quem_atende,
        "chamados": [
            {
                "data": c.criado_em.date().isoformat(),
                "tipo": labels_tipo.get(c.tipo, c.tipo),
                "prioridade": labels_prioridade.get(c.prioridade, c.prioridade),
                "status": labels_status.get(c.status, c.status),
                "responsavel": c.responsavel.nome if c.responsavel else "—",
                "descricao": c.descricao,
            }
            for c in chamados_periodo
        ],
    }


@app.get("/relatorios-dados/colaborador/{colaborador_id}")
def relatorio_por_colaborador(
    colaborador_id: int,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("relatorios")),
):
    colaborador = db.get(Colaborador, colaborador_id)
    if colaborador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador não encontrado")

    hoje = date.today()
    inicio = date.fromisoformat(data_inicio) if data_inicio else date(hoje.year, hoje.month, 1)
    fim = date.fromisoformat(data_fim) if data_fim else hoje
    if inicio > fim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data inicial nao pode ser depois da final")

    data_referencia = func.coalesce(ColaboradorEvento.data_inicio, func.date(ColaboradorEvento.criado_em))
    eventos = (
        db.query(ColaboradorEvento)
        .filter(ColaboradorEvento.colaborador_id == colaborador_id, data_referencia.between(inicio, fim))
        .order_by(ColaboradorEvento.criado_em.desc())
        .all()
    )

    labels_tipo = {t["chave"]: t["label"] for t in TIPOS_EVENTO_COLABORADOR}
    contagem_tipo: dict[str, int] = {}
    for e in eventos:
        contagem_tipo[e.tipo] = contagem_tipo.get(e.tipo, 0) + 1

    return {
        "colaborador": {
            "id": colaborador.id,
            "nome": colaborador.nome,
            "cargo": colaborador.cargo,
            "empresa_nome": colaborador.empresa.nome,
            "status": colaborador.status,
        },
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "total_eventos": len(eventos),
        "por_tipo": [{"tipo": labels_tipo.get(k, k), "total": v} for k, v in contagem_tipo.items()],
        "eventos": [
            {
                "data": (e.data_inicio.isoformat() if e.data_inicio else e.criado_em.date().isoformat()),
                "tipo": labels_tipo.get(e.tipo, e.tipo),
                "descricao": e.descricao or "—",
                "registrado_por": e.registrado_por.nome,
            }
            for e in eventos
        ],
    }


# ---------------------------------------------------------------------------
# Custos diarios (reembolso de despesas dos supervisores)
# ---------------------------------------------------------------------------

@app.get("/custos-diarios-dados-tipos")
def tipos_custo_diario(usuario: Usuario = Depends(usuario_atual)):
    return {"tipos": TIPOS_CUSTO_DIARIO}


def serializar_custo(c: CustoDiario) -> dict:
    return {
        "id": c.id,
        "usuario_id": c.usuario_id,
        "usuario_nome": c.usuario.nome,
        "tipo": c.tipo,
        "valor": c.valor,
        "data": c.data.isoformat(),
        "descricao": c.descricao,
        "nome_beneficiario": c.nome_beneficiario,
        "chave_pix": c.chave_pix,
        "tem_comprovante": c.comprovante_path is not None,
        "comprovante_nome_original": c.comprovante_nome_original,
        "reembolsado": c.reembolsado,
        "criado_em": c.criado_em.isoformat(),
    }


@app.get("/custos-diarios-dados")
def listar_custos_diarios(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    """Supervisor comum ve so os proprios custos; escritorio ve de todo mundo."""
    query = db.query(CustoDiario)
    if usuario.papel != "escritorio":
        query = query.filter(CustoDiario.usuario_id == usuario.id)
    if data_inicio:
        query = query.filter(CustoDiario.data >= date.fromisoformat(data_inicio))
    if data_fim:
        query = query.filter(CustoDiario.data <= date.fromisoformat(data_fim))
    custos = query.order_by(CustoDiario.data.desc(), CustoDiario.criado_em.desc()).all()
    return [serializar_custo(c) for c in custos]


@app.post("/custos-diarios-dados", status_code=status.HTTP_201_CREATED)
def criar_custo_diario(
    tipo: str = Form(...),
    valor: float = Form(...),
    data_custo: str = Form(...),
    descricao: str | None = Form(None),
    nome_beneficiario: str | None = Form(None),
    chave_pix: str | None = Form(None),
    comprovante: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if tipo not in CHAVES_TIPO_CUSTO_VALIDAS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de custo invalido")
    if valor <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O valor deve ser maior que zero")

    comprovante_path_salvo = None
    comprovante_nome_original = None
    if comprovante is not None and comprovante.filename:
        extensao = Path(comprovante.filename).suffix.lower()
        if extensao not in EXTENSOES_PERMITIDAS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comprovante deve ser JPEG, PNG ou PDF")
        conteudo = comprovante.file.read()
        if len(conteudo) > TAMANHO_MAXIMO_ARQUIVO:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo maior que 10MB")

        pasta_usuario = PASTA_UPLOADS_CUSTOS / str(usuario.id)
        pasta_usuario.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
        caminho_completo = pasta_usuario / nome_arquivo
        caminho_completo.write_bytes(conteudo)
        comprovante_path_salvo = str(caminho_completo)
        comprovante_nome_original = comprovante.filename

    custo = CustoDiario(
        usuario_id=usuario.id,
        tipo=tipo,
        valor=valor,
        data=date.fromisoformat(data_custo),
        descricao=descricao.strip() if descricao else None,
        nome_beneficiario=nome_beneficiario.strip() if nome_beneficiario else None,
        chave_pix=chave_pix.strip() if chave_pix else None,
        comprovante_path=comprovante_path_salvo,
        comprovante_nome_original=comprovante_nome_original,
    )
    db.add(custo)
    db.commit()
    db.refresh(custo)
    return serializar_custo(custo)


@app.patch("/custos-diarios-dados/{custo_id}")
def editar_custo_diario(
    custo_id: int,
    dados: CustoDiarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    custo = db.get(CustoDiario, custo_id)
    if custo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custo nao encontrado")
    if custo.usuario_id != usuario.id and usuario.papel != "escritorio":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Voce so pode editar seus proprios custos")

    campos = dados.model_dump(exclude_unset=True)

    if "reembolsado" in campos and usuario.papel != "escritorio":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="So o escritorio pode marcar como reembolsado")

    if "tipo" in campos:
        if campos["tipo"] not in CHAVES_TIPO_CUSTO_VALIDAS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de custo invalido")
        custo.tipo = campos["tipo"]
    if "valor" in campos:
        if campos["valor"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O valor deve ser maior que zero")
        custo.valor = campos["valor"]
    if "data" in campos:
        custo.data = date.fromisoformat(campos["data"])
    if "descricao" in campos:
        custo.descricao = campos["descricao"].strip() if campos["descricao"] else None
    if "nome_beneficiario" in campos:
        custo.nome_beneficiario = campos["nome_beneficiario"].strip() if campos["nome_beneficiario"] else None
    if "chave_pix" in campos:
        custo.chave_pix = campos["chave_pix"].strip() if campos["chave_pix"] else None
    if "reembolsado" in campos:
        custo.reembolsado = campos["reembolsado"]

    db.commit()
    db.refresh(custo)
    return serializar_custo(custo)


@app.delete("/custos-diarios-dados/{custo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_custo_diario(
    custo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    custo = db.get(CustoDiario, custo_id)
    if custo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custo nao encontrado")
    if custo.usuario_id != usuario.id and usuario.papel != "escritorio":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Voce so pode excluir seus proprios custos")

    if custo.comprovante_path and os.path.exists(custo.comprovante_path):
        os.remove(custo.comprovante_path)

    db.delete(custo)
    db.commit()


@app.get("/custos-diarios-dados/{custo_id}/comprovante")
def baixar_comprovante_custo(
    custo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    custo = db.get(CustoDiario, custo_id)
    if custo is None or not custo.comprovante_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comprovante nao encontrado")
    if custo.usuario_id != usuario.id and usuario.papel != "escritorio":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissao para ver esse comprovante")
    return FileResponse(custo.comprovante_path, filename=custo.comprovante_nome_original or "comprovante")


@app.post("/custos-diarios-dados/testar-email")
def testar_email_custos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_papel("escritorio")),
):
    """Dispara a checagem de custos pendentes e o envio do e-mail na hora, para teste."""
    try:
        resultado = verificar_e_enviar_custos(db)
        return resultado
    except RuntimeError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


# ---------------------------------------------------------------------------
# Periodo de experiencia (30/90 dias)
# ---------------------------------------------------------------------------

@app.get("/colaboradores-dados/experiencia/criticos")
def listar_experiencias_criticas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    """Colaboradores com checkpoint de experiencia vencendo em ate 7 dias - para o painel."""
    from alertas_experiencia import buscar_experiencias_criticas

    criticos = buscar_experiencias_criticas(db)
    return [
        {
            "colaborador_nome": c["colaborador_nome"],
            "empresa_nome": c["empresa_nome"],
            "checkpoint": c["checkpoint"],
            "data_checkpoint": c["data_checkpoint"].isoformat(),
            "dias_restantes": c["dias_restantes"],
        }
        for c in criticos
    ]


@app.post("/colaboradores-dados/experiencia/testar-email")
def testar_email_experiencia(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_papel("escritorio")),
):
    """Dispara a checagem de experiencia e o envio do e-mail na hora, para teste."""
    try:
        resultado = verificar_e_enviar_experiencias(db)
        return resultado
    except RuntimeError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


# ---------------------------------------------------------------------------
# Controle de estoque (EPI / uniformes)
# ---------------------------------------------------------------------------

def serializar_item_estoque(item: EstoqueItem) -> dict:
    return {
        "id": item.id,
        "empresa_id": item.empresa_id,
        "empresa_nome": item.empresa.nome if item.empresa_id else "Geral",
        "tipo_peca": item.tipo_peca,
        "tamanho": item.tamanho,
        "quantidade_atual": item.quantidade_atual,
        "ativo": item.ativo,
    }


def serializar_movimento_estoque(m: EstoqueMovimento) -> dict:
    return {
        "id": m.id,
        "item_id": m.item_id,
        "tipo": m.tipo,
        "quantidade": m.quantidade,
        "motivo": m.motivo,
        "colaborador_id": m.colaborador_id,
        "colaborador_nome": m.colaborador.nome if m.colaborador else None,
        "registrado_por": m.registrado_por.nome,
        "criado_em": m.criado_em.isoformat(),
    }


@app.get("/estoque-dados")
def listar_estoque(
    empresa_id: int | None = None,
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("estoque")),
):
    query = db.query(EstoqueItem)
    if empresa_id is not None:
        query = query.filter(EstoqueItem.empresa_id == empresa_id)
    if not incluir_inativos:
        query = query.filter(EstoqueItem.ativo.is_(True))
    itens = query.order_by(EstoqueItem.tipo_peca, EstoqueItem.tamanho).all()
    return [serializar_item_estoque(i) for i in itens]


@app.post("/estoque-dados", status_code=status.HTTP_201_CREATED)
def criar_item_estoque(
    dados: EstoqueItemCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("estoque")),
):
    if dados.empresa_id is not None and db.get(Empresa, dados.empresa_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa invalida")

    tipo_peca = dados.tipo_peca.strip().upper()
    tamanho = dados.tamanho.strip().upper()
    if not tipo_peca or not tamanho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o tipo de peca e o tamanho")
    if dados.quantidade_inicial < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade nao pode ser negativa")

    existente = db.query(EstoqueItem).filter_by(empresa_id=dados.empresa_id, tipo_peca=tipo_peca, tamanho=tamanho).first()
    if existente is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ja existe esse item (peca+tamanho) para essa empresa")

    item = EstoqueItem(
        empresa_id=dados.empresa_id,
        tipo_peca=tipo_peca,
        tamanho=tamanho,
        quantidade_atual=dados.quantidade_inicial,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serializar_item_estoque(item)


@app.patch("/estoque-dados/{item_id}")
def editar_item_estoque(
    item_id: int,
    dados: EstoqueItemUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("estoque")),
):
    item = db.get(EstoqueItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if "empresa_id" in campos:
        if campos["empresa_id"] is not None and db.get(Empresa, campos["empresa_id"]) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa invalida")
        item.empresa_id = campos["empresa_id"]
    if "tipo_peca" in campos:
        item.tipo_peca = campos["tipo_peca"].strip().upper()
    if "tamanho" in campos:
        item.tamanho = campos["tamanho"].strip().upper()
    if "ativo" in campos:
        item.ativo = campos["ativo"]

    db.commit()
    db.refresh(item)
    return serializar_item_estoque(item)


@app.delete("/estoque-dados/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_item_estoque(
    item_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("estoque")),
):
    item = db.get(EstoqueItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    db.query(EstoqueMovimento).filter_by(item_id=item_id).delete()
    db.delete(item)
    db.commit()


@app.get("/estoque-dados/{item_id}/movimentos")
def listar_movimentos_estoque(
    item_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("estoque")),
):
    if db.get(EstoqueItem, item_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    movimentos = (
        db.query(EstoqueMovimento)
        .filter_by(item_id=item_id)
        .order_by(EstoqueMovimento.criado_em.desc())
        .all()
    )
    return [serializar_movimento_estoque(m) for m in movimentos]


@app.post("/estoque-dados/{item_id}/movimentos", status_code=status.HTTP_201_CREATED)
def criar_movimento_estoque(
    item_id: int,
    dados: EstoqueMovimentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("estoque")),
):
    item = db.get(EstoqueItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    if dados.tipo not in ("entrada", "saida"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo deve ser entrada ou saida")
    if dados.quantidade <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade deve ser maior que zero")
    if dados.colaborador_id is not None and db.get(Colaborador, dados.colaborador_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador invalido")

    if dados.tipo == "saida" and dados.quantidade > item.quantidade_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estoque insuficiente (disponivel: {item.quantidade_atual})",
        )

    movimento = EstoqueMovimento(
        item_id=item_id,
        tipo=dados.tipo,
        quantidade=dados.quantidade,
        motivo=dados.motivo.strip() if dados.motivo else None,
        colaborador_id=dados.colaborador_id,
        registrado_por_id=usuario.id,
    )
    db.add(movimento)

    if dados.tipo == "entrada":
        item.quantidade_atual += dados.quantidade
    else:
        item.quantidade_atual -= dados.quantidade

    db.commit()
    db.refresh(movimento)
    return serializar_movimento_estoque(movimento)


# ---------------------------------------------------------------------------
# METLIFE (titular + dependentes)
# ---------------------------------------------------------------------------

def serializar_metlife(m: MetlifeLancamento) -> dict:
    return {
        "id": m.id,
        "colaborador_id": m.colaborador_id,
        "nome_dependente": m.nome_dependente,
        "valor": m.valor,
        "desconta": m.desconta,
        "data_inclusao": m.data_inclusao.isoformat() if m.data_inclusao else None,
        "data_exclusao": m.data_exclusao.isoformat() if m.data_exclusao else None,
    }


@app.get("/colaboradores-dados/{colaborador_id}/metlife")
def listar_metlife_colaborador(
    colaborador_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if db.get(Colaborador, colaborador_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador nao encontrado")
    lancamentos = db.query(MetlifeLancamento).filter_by(colaborador_id=colaborador_id).all()
    return [serializar_metlife(m) for m in lancamentos]


@app.post("/colaboradores-dados/{colaborador_id}/metlife", status_code=status.HTTP_201_CREATED)
def criar_metlife(
    colaborador_id: int,
    dados: MetlifeLancamentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if db.get(Colaborador, colaborador_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador nao encontrado")

    lancamento = MetlifeLancamento(
        colaborador_id=colaborador_id,
        nome_dependente=dados.nome_dependente.strip() if dados.nome_dependente else None,
        valor=dados.valor,
        desconta=dados.desconta,
        data_inclusao=date.fromisoformat(dados.data_inclusao) if dados.data_inclusao else None,
        data_exclusao=date.fromisoformat(dados.data_exclusao) if dados.data_exclusao else None,
    )
    db.add(lancamento)
    db.commit()
    db.refresh(lancamento)
    return serializar_metlife(lancamento)


@app.patch("/colaboradores-dados/metlife/{lancamento_id}")
def editar_metlife(
    lancamento_id: int,
    dados: MetlifeLancamentoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    lancamento = db.get(MetlifeLancamento, lancamento_id)
    if lancamento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lancamento nao encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if "nome_dependente" in campos:
        lancamento.nome_dependente = campos["nome_dependente"].strip() if campos["nome_dependente"] else None
    if "valor" in campos:
        lancamento.valor = campos["valor"]
    if "desconta" in campos:
        lancamento.desconta = campos["desconta"]
    if "data_inclusao" in campos:
        valor = campos["data_inclusao"]
        lancamento.data_inclusao = date.fromisoformat(valor) if valor else None
    if "data_exclusao" in campos:
        valor = campos["data_exclusao"]
        lancamento.data_exclusao = date.fromisoformat(valor) if valor else None

    db.commit()
    db.refresh(lancamento)
    return serializar_metlife(lancamento)


@app.delete("/colaboradores-dados/metlife/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_metlife(
    lancamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    lancamento = db.get(MetlifeLancamento, lancamento_id)
    if lancamento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lancamento nao encontrado")
    db.delete(lancamento)
    db.commit()


# ---------------------------------------------------------------------------
# Historico do mapa de servico
# ---------------------------------------------------------------------------

def _calcular_duracao_dias(data_inicio: date, data_fim: date | None) -> int:
    fim = data_fim or date.today()
    return (fim - data_inicio).days


def _formatar_duracao(dias: int) -> str:
    if dias < 30:
        return f"{dias} dia(s)"
    meses = dias // 30
    dias_restantes = dias % 30
    if meses < 12:
        texto = f"{meses} mes(es)"
        if dias_restantes:
            texto += f" e {dias_restantes} dia(s)"
        return texto
    anos = meses // 12
    meses_restantes = meses % 12
    texto = f"{anos} ano(s)"
    if meses_restantes:
        texto += f" e {meses_restantes} mes(es)"
    return texto


@app.get("/mapa-servico-historico")
def listar_historico_mapa_servico(
    colaborador_id: int | None = None,
    cliente_id: int | None = None,
    status_vinculo: str = "todos",
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("mapa_servico")),
):
    query = db.query(HorarioServico)
    if colaborador_id is not None:
        query = query.filter(HorarioServico.colaborador_id == colaborador_id)
    if cliente_id is not None:
        query = query.filter(HorarioServico.cliente_id == cliente_id)
    if status_vinculo == "ativos":
        query = query.filter(HorarioServico.data_fim.is_(None))
    elif status_vinculo == "encerrados":
        query = query.filter(HorarioServico.data_fim.isnot(None))

    registros = query.order_by(HorarioServico.data_inicio.desc()).all()

    resultado = []
    for h in registros:
        dias = _calcular_duracao_dias(h.data_inicio, h.data_fim)
        resultado.append(
            {
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
                "data_inicio": h.data_inicio.isoformat(),
                "data_fim": h.data_fim.isoformat() if h.data_fim else None,
                "ativo": h.data_fim is None,
                "duracao_dias": dias,
                "duracao_texto": _formatar_duracao(dias),
            }
        )
    return resultado


@app.get("/mapa-servico-historico/{horario_id}/eventos")
def listar_eventos_horario(
    horario_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_modulo("mapa_servico")),
):
    if db.get(HorarioServico, horario_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Horario nao encontrado")

    eventos = (
        db.query(HistoricoMapaServico)
        .filter_by(horario_servico_id=horario_id)
        .order_by(HistoricoMapaServico.criado_em.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "tipo_evento": e.tipo_evento,
            "dia_semana": e.dia_semana,
            "turno": e.turno,
            "hora_inicio": e.hora_inicio,
            "hora_fim": e.hora_fim,
            "motivo": e.motivo,
            "registrado_por": e.registrado_por.nome,
            "criado_em": e.criado_em.isoformat(),
        }
        for e in eventos
    ]



