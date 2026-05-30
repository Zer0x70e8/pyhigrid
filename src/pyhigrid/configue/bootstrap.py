#
""""""

def build_configue():
    from .configue import Configue
    return Configue()

def register_configue(container):
    # 依赖于 database, logger 等
    container.register(
        "configur",
        build_configue
    )

# alias
register = register_configue
