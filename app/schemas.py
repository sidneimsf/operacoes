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


class ClienteUpdate(BaseModel):
    empresa_id: int | None = None
    nome: str | None = None
    cnpj: str | None = None
    municipio: str | None = None
    ativo: bool | None = None


class ColaboradorCreate(BaseModel):
    empresa_id: int
    nome: str
    registro: str | None = None
    cargo: str | None = None
    contato: str | None = None
    data_admissao: str | None = None
    supervisor_id: int | None = None
    status: str = "ativo"


class ColaboradorUpdate(BaseModel):
    empresa_id: int | None = None
    nome: str | None = None
    registro: str | None = None
    cargo: str | None = None
    contato: str | None = None
    data_admissao: str | None = None
    supervisor_id: int | None = None
    status: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    nome: str
    papel: str


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    papel: str

    class Config:
        from_attributes = True
