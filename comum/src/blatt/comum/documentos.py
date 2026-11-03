"""Validação de CPF e CNPJ, inclusive o CNPJ alfanumérico.

Regras dos dígitos verificadores (módulo 11):
- CPF: pesos 10..2 e 11..2 sobre os 9 e 10 primeiros dígitos.
- CNPJ: pesos 5,4,3,2,9,8,7,6,5,4,3,2 e 6,5,4,3,2,9,8,7,6,5,4,3,2. No CNPJ alfanumérico
  (Instrução Normativa RFB 2.229/2024), as 12 primeiras posições aceitam letras maiúsculas
  e cada caractere vale o seu código ASCII menos 48 (dígitos continuam valendo 0 a 9); os
  dois verificadores continuam numéricos.
Em ambos, resto menor que 2 dá dígito 0; senão, 11 menos o resto.
"""

import re

# Só ASCII: "\d" aceitaria dígitos de outros alfabetos, e "$" aceitaria "\n" no fim.
_CPF = re.compile(r"[0-9]{11}")
_CNPJ = re.compile(r"[A-Z0-9]{12}[0-9]{2}")
_CNPJ_BASE = re.compile(r"[A-Z0-9]{8}")


def _digito(valores: list[int], pesos: list[int]) -> int:
    resto = sum(v * p for v, p in zip(valores, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(cpf: str) -> bool:
    if not _CPF.fullmatch(cpf) or len(set(cpf)) == 1:
        return False
    numeros = [int(c) for c in cpf]
    primeiro = _digito(numeros[:9], list(range(10, 1, -1)))
    segundo = _digito(numeros[:10], list(range(11, 1, -1)))
    return numeros[9:] == [primeiro, segundo]


def cnpj_valido(cnpj: str) -> bool:
    if not _CNPJ.fullmatch(cnpj) or len(set(cnpj)) == 1:
        return False
    valores = [ord(c) - 48 for c in cnpj]
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    primeiro = _digito(valores[:12], pesos[1:])
    segundo = _digito(valores[:13], pesos)
    return valores[12:] == [primeiro, segundo]


def cnpj_base_valida(base: str) -> bool:
    """Raiz do CNPJ (8 posições). Não tem dígito verificador próprio."""
    return bool(_CNPJ_BASE.fullmatch(base))
