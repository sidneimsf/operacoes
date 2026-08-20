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
