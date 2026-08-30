from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    senha: str


class ChamadoCreate(BaseModel):
    cliente_id: int
    tipo: str
    prioridade: str = "normal"
    descricao: str
    responsavel_id: int


class ChamadoStatusUpdate(BaseModel):
    status: str


class ChamadoFinalizar(BaseModel):
    pendencia: bool
    pendencia_detalhe: str | None = None
    documento_enviado: bool
    documento_detalhe: str | None = None
    observacoes: str | None = None


class AvisoCreate(BaseModel):
    mensagem: str
    destinatario_id: int | None = None


class ClienteCreate(BaseModel):
    empresa_id: int
    nome: str
    cnpj: str | None = None
    municipio: str | None = None
    endereco: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    responsavel_nome: str | None = None
    responsavel_telefone: str | None = None
    senha_acesso: str | None = None
    chave_acesso: str | None = None
    supervisor_id: int | None = None


class ClienteUpdate(BaseModel):
    empresa_id: int | None = None
    nome: str | None = None
    cnpj: str | None = None
    municipio: str | None = None
    endereco: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    responsavel_nome: str | None = None
    responsavel_telefone: str | None = None
    senha_acesso: str | None = None
    chave_acesso: str | None = None
    supervisor_id: int | None = None
    ativo: bool | None = None


class ColaboradorCreate(BaseModel):
    empresa_id: int
    nome: str
    registro: str | None = None
    cargo: str | None = None
    contato: str | None = None
    data_admissao: str | None = None
    aniversario_dia: int | None = None
    aniversario_mes: int | None = None
    supervisor_id: int | None = None
    status: str = "ativo"


class ColaboradorUpdate(BaseModel):
    empresa_id: int | None = None
    nome: str | None = None
    registro: str | None = None
    cargo: str | None = None
    contato: str | None = None
    data_admissao: str | None = None
    aniversario_dia: int | None = None
    aniversario_mes: int | None = None
    data_fim_experiencia_30: str | None = None
    data_fim_experiencia_90: str | None = None
    vt_numero_cartao: str | None = None
    vt_situacao: str | None = None
    vt_saldo: float | None = None
    seguro_vida_data_inclusao: str | None = None
    seguro_vida_data_exclusao: str | None = None
    supervisor_id: int | None = None
    status: str | None = None


class MetlifeLancamentoCreate(BaseModel):
    nome_dependente: str | None = None
    valor: float | None = None
    desconta: bool = False
    data_inclusao: str | None = None
    data_exclusao: str | None = None


class MetlifeLancamentoUpdate(BaseModel):
    nome_dependente: str | None = None
    valor: float | None = None
    desconta: bool | None = None
    data_inclusao: str | None = None
    data_exclusao: str | None = None


class ColaboradorEventoUpdate(BaseModel):
    descricao: str | None = None
    data_inicio: str | None = None
    data_fim: str | None = None


class HorarioServicoCreate(BaseModel):
    colaborador_id: int
    cliente_id: int
    dia_semana: str
    turno: str
    hora_inicio: str
    hora_fim: str


class HorarioServicoUpdate(BaseModel):
    colaborador_id: int | None = None
    cliente_id: int | None = None
    dia_semana: str | None = None
    turno: str | None = None
    hora_inicio: str | None = None
    hora_fim: str | None = None


class VeiculoCreate(BaseModel):
    placa: str
    modelo: str = "Fiat Mobi"
    ano: int | None = None
    apelido: str | None = None
    km_atual: int = 0


class VeiculoUpdate(BaseModel):
    placa: str | None = None
    modelo: str | None = None
    ano: int | None = None
    apelido: str | None = None
    km_atual: int | None = None
    ativo: bool | None = None


class ManutencaoVeiculoCreate(BaseModel):
    tipo: str
    data: str
    km: int
    descricao: str
    custo: float | None = None


class ManutencaoVeiculoUpdate(BaseModel):
    tipo: str | None = None
    data: str | None = None
    km: int | None = None
    descricao: str | None = None
    custo: float | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    nome: str
    papel: str
    super_admin: bool = False


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    papel: str

    class Config:
        from_attributes = True


class PermissaoUpdate(BaseModel):
    habilitado: bool


class UsuarioAcessoUpdate(BaseModel):
    email: str | None = None
    nova_senha: str | None = None


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    papel: str


class CustoDiarioUpdate(BaseModel):
    tipo: str | None = None
    valor: float | None = None
    data: str | None = None
    descricao: str | None = None
    nome_beneficiario: str | None = None
    chave_pix: str | None = None
    reembolsado: bool | None = None


class EstoqueItemCreate(BaseModel):
    empresa_id: int | None = None
    tipo_peca: str
    tamanho: str
    quantidade_inicial: int = 0


class EstoqueItemUpdate(BaseModel):
    empresa_id: int | None = None
    tipo_peca: str | None = None
    tamanho: str | None = None
    ativo: bool | None = None


class EstoqueMovimentoCreate(BaseModel):
    tipo: str
    quantidade: int
    motivo: str | None = None
    colaborador_id: int | None = None
