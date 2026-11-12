"""Regras de texto do eSocial usadas por mais de um módulo (cadastro e folha).

REGRA_CARACTERE_ESPECIAL: seção de regras gerais dos leiautes S-1.3,
https://www.gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-versao-s-1-3-nt-07-2026-rev-20-10-2026/index.html
"""

# ASCII imprimível, espaço simples e a lista de caracteres Latin-1 transcrita da regra.
_CARACTERES_PERMITIDOS = frozenset(
    [chr(c) for c in range(0x20, 0x7F)]
    + list("¡¢£¥§©ª«¬®¯°±²³µ¶·¹º»")
    + [chr(c) for c in range(0xC0, 0x100)]
)


def exigir_texto_permitido(campo: str, texto: str) -> None:
    """Aplica a REGRA_CARACTERE_ESPECIAL (leiautes S-1.3): só caracteres da lista oficial,
    sem espaço no início ou no fim (tabulação, quebra de linha e espaço sem quebra já ficam
    fora da lista)."""
    proibidos = sorted({c for c in texto if c not in _CARACTERES_PERMITIDOS})
    if proibidos:
        raise ValueError(f"{campo} tem caracteres não aceitos pelo eSocial: {proibidos!r}")
    if texto != texto.strip(" "):
        raise ValueError(f"{campo} não pode começar nem terminar com espaço")


def exigir_codigo_do_empregador(campo: str, codigo: str, tamanho_maximo: int) -> None:
    """Códigos atribuídos pelo empregador (codRubr, ideTabRubr, codLotacao): de 1 até o
    tamanho máximo, sem a expressão 'eSocial' nas 7 primeiras posições e dentro da
    REGRA_CARACTERE_ESPECIAL."""
    if not 1 <= len(codigo) <= tamanho_maximo:
        raise ValueError(f"{campo} deve ter de 1 a {tamanho_maximo} caracteres: {codigo!r}")
    if codigo[:7].lower() == "esocial":
        raise ValueError(f"{campo} não pode começar com 'eSocial': {codigo!r}")
    exigir_texto_permitido(campo, codigo)


def exigir_texto_livre(campo: str, texto: str, tamanho_maximo: int) -> None:
    """Campos de texto livre sem a REGRA_CARACTERE_ESPECIAL no leiaute (ex.: dscRubr,
    observacao). O XSD só exige o primeiro caractere diferente de espaço; o Blatt também
    recusa caracteres de controle (tabulação, quebra de linha) e espaço no fim, que nesses
    campos só aparecem por erro de digitação e iriam para o XML assinado."""
    if not 1 <= len(texto) <= tamanho_maximo:
        raise ValueError(f"{campo}: de 1 a {tamanho_maximo} caracteres")
    if texto != texto.strip():
        raise ValueError(f"{campo} não pode começar nem terminar com espaço")
    if any(not c.isprintable() for c in texto):
        raise ValueError(f"{campo} tem caracteres de controle (tabulação, quebra de linha)")
