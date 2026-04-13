from __future__ import annotations


def _left_zero(value: str | int, length: int) -> str:
    s = str(value).strip()
    if len(s) > length:
        return s[-length:]
    return s.zfill(length)


def calcular_digito_verificador(cdc_sin_dv: str, base_max: int = 11) -> int:
    """Algoritmo módulo 11 (SET / e-Kuatia). Entrada alfanumérica; dígitos no numéricos se reemplazan por código ASCII."""
    v_numero_al = ""
    for ch in cdc_sin_dv.upper():
        o = ord(ch)
        if 48 <= o <= 57:
            v_numero_al += ch
        else:
            v_numero_al += str(o)

    k = 2
    v_total = 0
    for i in range(len(v_numero_al), 0, -1):
        if k > base_max:
            k = 2
        v_numero_aux = int(v_numero_al[i - 1 : i])
        v_total += v_numero_aux * k
        k += 1

    v_resto = v_total % 11
    if v_resto > 1:
        return 11 - v_resto
    return 0


def generar_cdc(
    *,
    ruc_con_dv: str,
    tipo_documento: int,
    establecimiento: str,
    punto_expedicion: str,
    numero_documento: int,
    tipo_contribuyente: int,
    fecha_emision_iso_date: str,
    tipo_emision: int,
    codigo_seguridad_9: str,
) -> str:
    """
    CDC de 44 caracteres: 43 + dígito verificador.
    ruc_con_dv: formato '99999999-9'
    fecha_emision_iso_date: 'YYYY-MM-DD'
    """
    if "-" not in ruc_con_dv:
        raise ValueError("El RUC debe incluir DV, ej. 00000001-9")

    partes = ruc_con_dv.split("-", 1)
    ruc_emisor = _left_zero(partes[0], 8)
    dv_emisor = partes[1][:1]
    est = _left_zero(establecimiento, 3)
    punto = _left_zero(punto_expedicion, 3)
    numero = _left_zero(numero_documento, 7)
    fecha = fecha_emision_iso_date.replace("-", "")[:8]
    if len(fecha) != 8:
        raise ValueError("Fecha inválida")

    cod_seg = _left_zero(codigo_seguridad_9, 9)

    cdc = (
        _left_zero(tipo_documento, 2)
        + ruc_emisor
        + dv_emisor
        + est
        + punto
        + numero
        + str(tipo_contribuyente)[0]
        + fecha
        + str(tipo_emision)[0]
        + cod_seg
    )

    if len(cdc) != 43:
        raise ValueError(f"Longitud CDC base incorrecta: {len(cdc)}")

    dv = calcular_digito_verificador(cdc, 11)
    return cdc + str(dv)
