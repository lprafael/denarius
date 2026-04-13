from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LineaCalculo:
    d_p_uni_pro_ser: int
    d_cant_pro_ser: float
    d_tasa_iva: int


@dataclass
class TotalesDE:
    d_sub_exe: int
    d_sub_exo: int
    d_sub5: int
    d_sub10: int
    d_tot_ope: int
    d_tot_desc: int
    d_tot_desc_glotem: int
    d_tot_ant_item: int
    d_tot_ant: int
    d_porc_desc_total: int
    d_desc_total: str
    d_anticipo: int
    d_redon: str
    d_tot_gral_ope: int
    d_iva5: int
    d_iva10: int
    d_tot_iva: int
    d_base_grav5: int
    d_base_grav10: int
    d_t_bas_gra_iva: int


@dataclass
class LineaIVADetail:
    d_tot_bru_ope_item: int
    d_bas_grav_iva: int
    d_liq_iva_item: int


def _iva_desde_precio_incluido(precio_unitario: int, tasa: int) -> tuple[int, int]:
    if tasa not in (5, 10, 0):
        raise ValueError("Tasa IVA soportada: 0, 5 o 10")
    if tasa == 0:
        return 0, 0
    bruto = round(precio_unitario * 100 / (100 + tasa))
    iva = precio_unitario - bruto
    return bruto, iva


def calcular_totales_lineas(lineas: list[LineaCalculo]) -> tuple[list[LineaIVADetail], TotalesDE]:
    detalles: list[LineaIVADetail] = []
    d_sub5 = 0
    d_sub10 = 0
    d_sub_exe = 0
    d_iva5 = 0
    d_iva10 = 0
    d_base5 = 0
    d_base10 = 0

    for ln in lineas:
        cant = float(ln.d_cant_pro_ser)
        tot_bru = int(round(ln.d_p_uni_pro_ser * cant))
        base_u, iva_u = _iva_desde_precio_incluido(ln.d_p_uni_pro_ser, ln.d_tasa_iva)

        if ln.d_tasa_iva == 10:
            d_sub10 += tot_bru
            bg = int(round(base_u * cant))
            li = int(round(iva_u * cant))
            d_base10 += bg
            d_iva10 += li
            detalles.append(LineaIVADetail(d_tot_bru_ope_item=tot_bru, d_bas_grav_iva=bg, d_liq_iva_item=li))
        elif ln.d_tasa_iva == 5:
            d_sub5 += tot_bru
            bg = int(round(base_u * cant))
            li = int(round(iva_u * cant))
            d_base5 += bg
            d_iva5 += li
            detalles.append(LineaIVADetail(d_tot_bru_ope_item=tot_bru, d_bas_grav_iva=bg, d_liq_iva_item=li))
        elif ln.d_tasa_iva == 0:
            d_sub_exe += tot_bru
            detalles.append(LineaIVADetail(d_tot_bru_ope_item=tot_bru, d_bas_grav_iva=0, d_liq_iva_item=0))
        else:
            raise ValueError(f"Tasa IVA no soportada: {ln.d_tasa_iva}")

    d_tot_ope = d_sub5 + d_sub10 + d_sub_exe
    d_tot_iva = d_iva5 + d_iva10
    d_t_bas = d_base5 + d_base10

    tot = TotalesDE(
        d_sub_exe=d_sub_exe,
        d_sub_exo=0,
        d_sub5=d_sub5,
        d_sub10=d_sub10,
        d_tot_ope=d_tot_ope,
        d_tot_desc=0,
        d_tot_desc_glotem=0,
        d_tot_ant_item=0,
        d_tot_ant=0,
        d_porc_desc_total=0,
        d_desc_total="0.0",
        d_anticipo=0,
        d_redon="0.0",
        d_tot_gral_ope=d_tot_ope,
        d_iva5=d_iva5,
        d_iva10=d_iva10,
        d_tot_iva=d_tot_iva,
        d_base_grav5=d_base5,
        d_base_grav10=d_base10,
        d_t_bas_gra_iva=d_t_bas,
    )
    return detalles, tot
