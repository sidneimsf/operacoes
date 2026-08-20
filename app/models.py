from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Chamado(Base):
    """
    Chamado aberto pelo escritorio ou supervisor para um cliente:
    manutencao, material de limpeza, uniforme, documento, folha de
    ponto, reclamacao, seguranca, comercial ou outros. A tela de
    Ocorrencias monitora esses chamados por status/tipo/cliente/data.
    """
    __tablename__ = "chamados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    prioridade: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    descricao: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="novo")
    aberto_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    responsavel_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora_utc, onupdate=agora_utc
    )

    # Preenchidos no checklist de encerramento (so quando status vira finalizado)
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    confirmacao_vista: Mapped[bool] = mapped_column(Boolean, default=False)
    fechamento_pendencia: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fechamento_pendencia_detalhe: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fechamento_documento_enviado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fechamento_documento_detalhe: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fechamento_observacoes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    cliente: Mapped["Cliente"] = relationship()
    aberto_por: Mapped["Usuario"] = relationship(foreign_keys=[aberto_por_id])
    responsavel: Mapped["Usuario | None"] = relationship(foreign_keys=[responsavel_id])
    finalizado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[finalizado_por_id])

    def __repr__(self) -> str:
        return f"<Chamado {self.tipo} - {self.status}>"


class Aviso(Base):
    """
    Mural de avisos: qualquer usuario pode postar uma mensagem para
    todos ou para uma pessoa especifica. Aparece na tela de Avisos
    em formato de mural (estilo post-it).
    """
    __tablename__ = "avisos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mensagem: Mapped[str] = mapped_column(String(1000), nullable=False)
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    destinatario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    criado_por: Mapped["Usuario"] = relationship(foreign_keys=[criado_por_id])
    destinatario: Mapped["Usuario | None"] = relationship(foreign_keys=[destinatario_id])

    def __repr__(self) -> str:
        return f"<Aviso de {self.criado_por_id}>"


class Usuario(Base):
    """
    Quem efetivamente usa o app: supervisores (campo) e equipe do
    escritorio (gerente/assistentes). Colaboradores das zeladorias
    NAO tem usuario aqui - eles nao acessam o sistema.
    """
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), nullable=False)  # "supervisor" ou "escritorio"
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    avisos_vistos_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    def __repr__(self) -> str:
        return f"<Usuario {self.email} ({self.papel})>"


class Empresa(Base):
    """
    As 4 empresas que emitem cobranca: CORDSUL, KRETZER, STAR SUL, FLC.
    Cada uma tem sua propria lista de clientes.
    """
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    clientes: Mapped[list["Cliente"]] = relationship(
        back_populates="empresa", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Empresa {self.nome}>"


class Cliente(Base):
    """
    Um cliente atendido (local/unidade de prestacao de servico).
    Identificado pelo nome na tela; o CNPJ fica guardado para referencia
    interna (varios clientes podem compartilhar o mesmo CNPJ, como no
    caso de unidades de uma mesma rede).
    """
    __tablename__ = "clientes"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nome", name="uq_cliente_empresa_nome"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    municipio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    empresa: Mapped["Empresa"] = relationship(back_populates="clientes")
    colaboradores: Mapped[list["Colaborador"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Cliente {self.nome}>"


class Colaborador(Base):
    """
    Funcionario operacional (zeladoria, limpeza, etc.) vinculado a um
    cliente. Nao acessa o app - existe aqui so como registro, para
    o supervisor associar folha de ponto e documentos a alguem.
    """
    __tablename__ = "colaboradores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    cliente: Mapped["Cliente"] = relationship(back_populates="colaboradores")

    def __repr__(self) -> str:
        return f"<Colaborador {self.nome}>"
