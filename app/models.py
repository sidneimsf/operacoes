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
