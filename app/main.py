from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from database import get_db
from models import Cliente, Empresa

app = FastAPI(title="Operacoes SolarSync", version="0.1.0")


@app.get("/")
def root():
    return {"app": "operacoes.solarsync", "status": "em desenvolvimento"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/empresas")
def listar_empresas(db: Session = Depends(get_db)):
    empresas = db.query(Empresa).order_by(Empresa.nome).all()
    return [{"id": e.id, "nome": e.nome} for e in empresas]


@app.get("/clientes")
def listar_clientes(empresa_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Cliente)
    if empresa_id is not None:
        query = query.filter(Cliente.empresa_id == empresa_id)
    clientes = query.order_by(Cliente.nome).all()
    return [
        {"id": c.id, "nome": c.nome, "empresa_id": c.empresa_id, "cnpj": c.cnpj}
        for c in clientes
    ]


# Estrutura prevista para os proximos modulos (adicionar como routers):
#   /ponto       -> upload da folha de ponto digitalizada pelo supervisor
#   /documentos  -> integracao com a estrutura de pastas no Dropbox
