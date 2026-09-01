from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LineaCalculo:
    d_p_uni_pro_ser: int
    d_cant_pro_ser: float
    d_tasa_iva: int
    i_afec_iva: int = 1  # 1=Gravado, 2=Exonerado, 3=Exento, 4=Gravado parcial
    d_prop_iva: int = 100  # % de proporción gravada (0 a 100)
    d_desc_item: int = 0
    d_porc_des_it: float = 0.0


@dataclass
class LineaIVADetail:
    d_tot_bru_ope_item: int
    d_desc_item: int
    d_porc_des_it: float
    d_desc_glo_item: int
    d_tot_ope_item: int
    d_prop_iva: int
    d_tasa_iva: int
    d_bas_grav_iva: int
    d_liq_iva_item: int
    d_bas_exe_item: int = 0


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
    d_desc_total: int
    d_anticipo: int
    d_redon: int
    d_tot_gral_ope: int
    d_iva5: int
    d_iva10: int
    d_tot_iva: int
    d_base_grav5: int
    d_base_grav10: int
    d_t_bas_gra_iva: int


def _iva_desde_precio_incluido(precio_neto_item: int, tasa: int, prop_iva: int = 100) -> tuple[int, int]:
    """Calcula base imponible y liquidación IVA con precio que incluye impuesto."""
    if tasa not in (5, 10, 0):
        raise ValueError("Tasa IVA soportada: 0, 5 o 10")
    if tasa == 0 or prop_iva == 0:
        return 0, 0
    
    # Base gravada proporcional
    base_gravada = round((precio_neto_item * 100 / (100 + tasa)) * (prop_iva / 100.0))
    # Liquidación IVA proporcional
    liq_iva = round((precio_neto_item - (precio_neto_item * 100 / (100 + tasa))) * (prop_iva / 100.0))
    return int(base_gravada), int(liq_iva)


def calcular_totales_lineas(
    lineas: list[LineaCalculo],
    descuento_global: int = 0,
    anticipo_global: int = 0,
    redondeo: int = 0,
) -> tuple[list[LineaIVADetail], TotalesDE]:
    """
    Calcula los totales de cada ítem y los totales generales conforme al Manual Técnico v150 de SIFEN.
    """
    detalles: list[LineaIVADetail] = []
    d_sub5 = 0
    d_sub10 = 0
    d_sub_exe = 0
    d_sub_exo = 0
    d_tot_desc_items = 0
    d_base5 = 0
    d_base10 = 0
    d_iva5 = 0
    d_iva10 = 0

    # 1. Total bruto inicial
    total_bruto_operacion = sum(int(round(ln.d_p_uni_pro_ser * float(ln.d_cant_pro_ser))) for ln in lineas)

    for ln in lineas:
        cant = float(ln.d_cant_pro_ser)
        tot_bru = int(round(ln.d_p_uni_pro_ser * cant))
        
        # Descuento por ítem
        desc_item = int(ln.d_desc_item)
        if desc_item == 0 and ln.d_porc_des_it > 0:
            desc_item = int(round(tot_bru * (ln.d_porc_des_it / 100.0)))
        d_tot_desc_items += desc_item

        # Prorrateo de descuento global por ítem si aplica
        desc_glo_item = 0
        if descuento_global > 0 and total_bruto_operacion > 0:
            desc_glo_item = int(round(descuento_global * (tot_bru / total_bruto_operacion)))

        tot_ope_item = max(0, tot_bru - desc_item - desc_glo_item)

        # Determinar base gravada y liquidación según afectación
        prop = ln.d_prop_iva if ln.d_prop_iva > 0 else (100 if ln.d_tasa_iva in (5, 10) else 0)
        
        if ln.i_afec_iva == 2:  # Exonerado
            d_sub_exo += tot_ope_item
            detalles.append(
                LineaIVADetail(
                    d_tot_bru_ope_item=tot_bru,
                    d_desc_item=desc_item,
                    d_porc_des_it=ln.d_porc_des_it,
                    d_desc_glo_item=desc_glo_item,
                    d_tot_ope_item=tot_ope_item,
                    d_prop_iva=0,
                    d_tasa_iva=0,
                    d_bas_grav_iva=0,
                    d_liq_iva_item=0,
                    d_bas_exe_item=tot_ope_item,
                )
            )
        elif ln.i_afec_iva == 3 or ln.d_tasa_iva == 0:  # Exento
            d_sub_exe += tot_ope_item
            detalles.append(
                LineaIVADetail(
                    d_tot_bru_ope_item=tot_bru,
                    d_desc_item=desc_item,
                    d_porc_des_it=ln.d_porc_des_it,
                    d_desc_glo_item=desc_glo_item,
                    d_tot_ope_item=tot_ope_item,
                    d_prop_iva=0,
                    d_tasa_iva=0,
                    d_bas_grav_iva=0,
                    d_liq_iva_item=0,
                    d_bas_exe_item=tot_ope_item,
                )
            )
        elif ln.d_tasa_iva == 10:
            d_sub10 += tot_ope_item
            bg, li = _iva_desde_precio_incluido(tot_ope_item, 10, prop)
            d_base10 += bg
            d_iva10 += li
            detalles.append(
                LineaIVADetail(
                    d_tot_bru_ope_item=tot_bru,
                    d_desc_item=desc_item,
                    d_porc_des_it=ln.d_porc_des_it,
                    d_desc_glo_item=desc_glo_item,
                    d_tot_ope_item=tot_ope_item,
                    d_prop_iva=prop,
                    d_tasa_iva=10,
                    d_bas_grav_iva=bg,
                    d_liq_iva_item=li,
                    d_bas_exe_item=tot_ope_item - bg if prop < 100 else 0,
                )
            )
        elif ln.d_tasa_iva == 5:
            d_sub5 += tot_ope_item
            bg, li = _iva_desde_precio_incluido(tot_ope_item, 5, prop)
            d_base5 += bg
            d_iva5 += li
            detalles.append(
                LineaIVADetail(
                    d_tot_bru_ope_item=tot_bru,
                    d_desc_item=desc_item,
                    d_porc_des_it=ln.d_porc_des_it,
                    d_desc_glo_item=desc_glo_item,
                    d_tot_ope_item=tot_ope_item,
                    d_prop_iva=prop,
                    d_tasa_iva=5,
                    d_bas_grav_iva=bg,
                    d_liq_iva_item=li,
                    d_bas_exe_item=tot_ope_item - bg if prop < 100 else 0,
                )
            )
        else:
            raise ValueError(f"Tasa IVA no soportada: {ln.d_tasa_iva}")

    d_tot_ope = d_sub5 + d_sub10 + d_sub_exe + d_sub_exo
    d_tot_desc = d_tot_desc_items
    d_tot_desc_glotem = descuento_global
    d_desc_total = d_tot_desc + d_tot_desc_glotem
    d_porc_desc_total = int(round((d_desc_total / total_bruto_operacion * 100))) if total_bruto_operacion > 0 else 0
    d_tot_ant = anticipo_global
    d_tot_gral_ope = max(0, d_tot_ope - d_tot_ant + redondeo)
    d_tot_iva = d_iva5 + d_iva10
    d_t_bas = d_base5 + d_base10

    tot = TotalesDE(
        d_sub_exe=d_sub_exe,
        d_sub_exo=d_sub_exo,
        d_sub5=d_sub5,
        d_sub10=d_sub10,
        d_tot_ope=d_tot_ope,
        d_tot_desc=d_tot_desc,
        d_tot_desc_glotem=d_tot_desc_glotem,
        d_tot_ant_item=0,
        d_tot_ant=d_tot_ant,
        d_porc_desc_total=d_porc_desc_total,
        d_desc_total=d_desc_total,
        d_anticipo=d_tot_ant,
        d_redon=redondeo,
        d_tot_gral_ope=d_tot_gral_ope,
        d_iva5=d_iva5,
        d_iva10=d_iva10,
        d_tot_iva=d_tot_iva,
        d_base_grav5=d_base5,
        d_base_grav10=d_base10,
        d_t_bas_gra_iva=d_t_bas,
    )
    return detalles, tot
