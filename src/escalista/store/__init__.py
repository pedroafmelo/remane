"""Persistência da execução, das versões da escala e das aprovações (implementa a porta `Repository`)."""

# Registra as tabelas do acompanhamento no `Base.metadata` sempre que qualquer módulo de `store/` é importado, para
# que `init_db` crie `track_case` e `channel_message` sem o chamador precisar importá-las (C7, tarefa B1).
from escalista.store import tracking as _tracking  # noqa: F401
