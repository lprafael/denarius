import React, { useState, useEffect } from "react";
import {
  createFactura,
  consultarRuc,
  getClienteByRuc,
  upsertCliente,
  getGeoDepartamentos,
  getGeoDistritos,
  getGeoCiudades,
  type FacturaCreate,
  type GeoDepartamento,
  type GeoDistrito,
  type GeoCiudad,
} from "../api";

interface FacturacionViewProps {
  emisor: any;
  productos: any[];
  refresh: () => Promise<void>;
  initialFacturaParams: any;
}

export function FacturacionView({ emisor, productos, refresh, initialFacturaParams }: FacturacionViewProps) {
  const [tipoDoc, setTipoDoc] = useState<number>(1); // 1=Factura, 5=NC, 6=ND, 4=Autofactura, 2=Exportación, 7=Remisión
  const [ruc, setRuc] = useState(initialFacturaParams?.ruc || "");
  const [dv, setDv] = useState(initialFacturaParams?.dv || "");
  const [nombre, setNombre] = useState(initialFacturaParams?.nombre || "");
  const [clienteEmail, setClienteEmail] = useState(initialFacturaParams?.clienteEmail || "");
  const [clienteTel, setClienteTel] = useState(initialFacturaParams?.clienteTel || "");
  const [clienteDir, setClienteDir] = useState(initialFacturaParams?.clienteDir || "");
  
  // Geografía Oficial SIFEN
  const [deptoId, setDeptoId] = useState<number>(1);
  const [distritoId, setDistritoId] = useState<number>(1);
  const [ciudadId, setCiudadId] = useState<number>(1);

  const [deptos, setDeptos] = useState<GeoDepartamento[]>([]);
  const [distritosLocal, setDistritosLocal] = useState<GeoDistrito[]>([]);
  const [ciudadesLocal, setCiudadesLocal] = useState<GeoCiudad[]>([]);

  // Multidivisa y Condiciones
  const [moneda, setMoneda] = useState<string>("PYG");
  const [tipoCambio, setTipoCambio] = useState<number>(7500);
  const [condicionOpe, setCondicionOpe] = useState<number>(1); // 1=Contado, 2=Crédito
  const [plazoCredito, setPlazoCredito] = useState<string>("30");
  const [descuentoGlobal, setDescuentoGlobal] = useState<number>(0);
  const [redondeo, setRedondeo] = useState<number>(0);

  // Notas de Crédito / Débito (Doc Asociado)
  const [cdcAsociado, setCdcAsociado] = useState<string>("");
  const [motivoNC, setMotivoNC] = useState<number>(1);

  // Líneas de detalle
  const [lineas, setLineas] = useState<any[]>(
    initialFacturaParams?.lineas?.length > 0 
      ? initialFacturaParams.lineas 
      : [{ producto_id: undefined, d_cod_int: "ART001", d_des_pro_ser: "Producto o servicio", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10, d_desc_item: 0 }]
  );

  const [clienteEncontrado, setClienteEncontrado] = useState<any>(null);
  const [showClienteModal, setShowClienteModal] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [success, setSuccess] = useState("");

  // Cargar Departamentos al montar
  useEffect(() => {
    getGeoDepartamentos().then((d) => {
      setDeptos(d);
      if (d.length > 0 && !deptoId) setDeptoId(d[0].id);
    }).catch(console.error);
  }, []);

  // Cargar Distritos cuando cambia Departamento
  useEffect(() => {
    if (deptoId > 0) {
      getGeoDistritos(deptoId).then((dists) => {
        setDistritosLocal(dists);
        if (dists.length > 0) setDistritoId(dists[0].id);
      }).catch(console.error);
    }
  }, [deptoId]);

  // Cargar Ciudades cuando cambia Distrito
  useEffect(() => {
    if (distritoId > 0) {
      getGeoCiudades(distritoId, deptoId).then((cius) => {
        setCiudadesLocal(cius);
        if (cius.length > 0) setCiudadId(cius[0].id);
      }).catch(console.error);
    }
  }, [distritoId, deptoId]);

  async function onRucBlur(val: string) {
    if (!val) { setDv(""); setClienteEncontrado(null); return; }
    let total = 0;
    let k = 2;
    for (let i = val.length - 1; i >= 0; i--) {
      let b = val.charAt(i);
      if (b >= '0' && b <= '9') {
        total += parseInt(b) * k;
        k++;
        if (k > 11) k = 2;
      }
    }
    let r = total % 11;
    let calcDv = r > 1 ? (11 - r).toString() : "0";
    setDv(calcDv);

    try {
      const cli = await getClienteByRuc(val);
      if (cli) {
        setNombre(cli.razon_social);
        setClienteEmail(cli.email);
        setClienteTel(cli.telefono);
        setClienteDir(cli.direccion);
        if (cli.c_dep) setDeptoId(cli.c_dep);
        if (cli.c_dis) setDistritoId(cli.c_dis);
        if (cli.c_ciu) setCiudadId(cli.c_ciu);
        setDv(cli.ruc_con_dv.split('-')[1] || calcDv);
        setClienteEncontrado(cli);
        return;
      }
    } catch (e) {}

    if (val.length >= 5) {
      try {
        const res = await consultarRuc(val);
        if (res.ok && res.razon_social) {
          setNombre(res.razon_social);
          if (res.dv) setDv(res.dv);
          setClienteEncontrado({ _is_new_sifen: true });
        }
      } catch (err) {}
    }
  }

  // Cálculos en vivo para la vista
  const subtotalBruto = lineas.reduce((acc, l) => acc + (Number(l.d_p_uni_pro_ser) * Number(l.d_cant_pro_ser)), 0);
  const totalDescuentos = lineas.reduce((acc, l) => acc + Number(l.d_desc_item || 0), 0) + Number(descuentoGlobal || 0);
  const totalGeneral = Math.max(0, subtotalBruto - totalDescuentos + Number(redondeo || 0));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setErr(""); setSuccess("");
    try {
      const currentDepto = deptos.find(d => d.id === deptoId);
      const currentDist = distritosLocal.find(d => d.id === distritoId);
      const currentCiu = ciudadesLocal.find(c => c.id === ciudadId);

      const payload: FacturaCreate = {
        i_ti_de: tipoDoc,
        receptor_ruc: ruc,
        receptor_dv: dv,
        receptor_nombre: nombre,
        receptor_tel: clienteTel,
        receptor_dir: clienteDir,
        c_dep_rec: deptoId,
        d_des_dep_rec: currentDepto?.nombre || "CAPITAL",
        c_dis_rec: distritoId,
        d_des_dis_rec: currentDist?.nombre || "ASUNCION (DISTRITO)",
        c_ciu_rec: ciudadId,
        d_des_ciu_rec: currentCiu?.nombre || "ASUNCION (DISTRITO)",
        i_cond_ope: condicionOpe,
        d_plazo_cre: condicionOpe === 2 ? plazoCredito : "",
        moneda: moneda,
        tipo_cambio: moneda !== "PYG" ? tipoCambio : 1.0,
        descuento_global: Number(descuentoGlobal),
        redondeo: Number(redondeo),
        cdc_asociado: (tipoDoc === 5 || tipoDoc === 6) ? cdcAsociado : "",
        motivo_emision_nc: (tipoDoc === 5 || tipoDoc === 6) ? motivoNC : 1,
        lineas: lineas.map((l) => ({
          producto_id: l.producto_id,
          d_cod_int: l.d_cod_int || "ART",
          d_des_pro_ser: l.d_des_pro_ser,
          d_cant_pro_ser: Number(l.d_cant_pro_ser),
          d_p_uni_pro_ser: Math.round(Number(l.d_p_uni_pro_ser)),
          d_tasa_iva: Number(l.d_tasa_iva),
          i_afec_iva: Number(l.d_tasa_iva) > 0 ? 1 : 3,
          d_desc_item: Number(l.d_desc_item || 0),
        })),
        firmar: true,
      };

      const res = await createFactura(payload);
      setSuccess(`Documento Electrónico #${res.numero_documento} generado y firmado con éxito. CDC: ${res.cdc}`);

      // Auto-guardar cliente si es nuevo
      try {
        await upsertCliente({
          ruc_con_dv: `${ruc}-${dv}`,
          razon_social: nombre,
          email: clienteEmail,
          telefono: clienteTel,
          direccion: clienteDir,
          c_dep: deptoId,
          d_des_dep: currentDepto?.nombre || "",
          c_dis: distritoId,
          d_des_dis: currentDist?.nombre || "",
          c_ciu: ciudadId,
          d_des_ciu: currentCiu?.nombre || "",
        });
      } catch (err) {}

      // Limpiar formulario
      setRuc(""); setNombre(""); setCdcAsociado("");
      setLineas([{ producto_id: undefined, d_cod_int: "ART001", d_des_pro_ser: "Producto o servicio", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10, d_desc_item: 0 }]);
      await refresh();
    } catch (ex: any) {
      setErr(ex.message || String(ex));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid">
      {err && <div className="alert error" style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', gridColumn: '1/-1' }}>❌ {err}</div>}
      {success && <div className="alert success" style={{ background: '#dcfce7', color: '#166534', padding: '12px', borderRadius: '8px', gridColumn: '1/-1' }}>✅ {success}</div>}

      <div className="card wide">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>Emisión de Documento Electrónico (SIFEN v150)</h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label style={{ fontWeight: 'bold', fontSize: '13px' }}>Tipo de DE:</label>
            <select
              value={tipoDoc}
              onChange={(e) => setTipoDoc(Number(e.target.value))}
              style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontWeight: 'bold', background: '#f8fafc' }}
            >
              <option value={1}>📄 Factura Electrónica</option>
              <option value={5}>🔄 Nota de Crédito Electrónica</option>
              <option value={6}>➕ Nota de Débito Electrónica</option>
              <option value={4}>👤 Autofactura Electrónica</option>
              <option value={2}>🚢 Factura de Exportación</option>
              <option value={7}>🚚 Nota de Remisión</option>
            </select>
          </div>
        </div>

        <form onSubmit={onSubmit} className="form">
          {/* Si es Nota de Crédito o Débito, solicitar documento asociado */}
          {(tipoDoc === 5 || tipoDoc === 6) && (
            <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', padding: '12px', marginBottom: '15px' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#1e40af' }}>🔗 Documento Asociado / Referenciado</h4>
              <div className="h-stack" style={{ gap: '1rem' }}>
                <label style={{ flex: 3 }}>
                  CDC de Factura Afectada (44 dígitos):
                  <input
                    placeholder="01800000000000000000000000000000000000000000"
                    value={cdcAsociado}
                    onChange={(e) => setCdcAsociado(e.target.value)}
                    required
                  />
                </label>
                <label style={{ flex: 2 }}>
                  Motivo de Emisión:
                  <select value={motivoNC} onChange={(e) => setMotivoNC(Number(e.target.value))}>
                    <option value={1}>1 - Devolución</option>
                    <option value={2}>2 - Descuento</option>
                    <option value={3}>3 - Bonificación</option>
                    <option value={4}>4 - Crédito Incobrable</option>
                    <option value={7}>7 - Anulación</option>
                  </select>
                </label>
              </div>
            </div>
          )}

          {/* Datos del Receptor / Cliente */}
          <div className="h-stack" style={{ gap: '1rem' }}>
            <label style={{ flex: 2 }}>RUC / Documento <input value={ruc} onChange={e=>setRuc(e.target.value)} onBlur={e=>onRucBlur(e.target.value)} required /></label>
            <label style={{ flex: 1 }}>DV <input value={dv} onChange={e=>setDv(e.target.value)} maxLength={2} /></label>
            <label style={{ flex: 4 }}>Nombre / Razón Social <input value={nombre} onChange={e=>setNombre(e.target.value)} required /></label>
          </div>

          <div className="h-stack" style={{ gap: '1rem' }}>
            <label style={{ flex: 2 }}>Dirección <input value={clienteDir} onChange={e=>setClienteDir(e.target.value)} /></label>
            <label style={{ flex: 1 }}>Teléfono <input value={clienteTel} onChange={e=>setClienteTel(e.target.value)} /></label>
            <label style={{ flex: 2 }}>Email <input value={clienteEmail} onChange={e=>setClienteEmail(e.target.value)} /></label>
          </div>

          {/* Geografía Oficial SIFEN */}
          <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', marginTop: '10px', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px' }}>
              📍 Localidad SIFEN (Catálogo Oficial DNIT Noviembre 2025):
            </span>
            <div className="h-stack" style={{ gap: '10px' }}>
              <label style={{ flex: 1, fontSize: '12px' }}>
                Departamento:
                <select value={deptoId} onChange={(e) => setDeptoId(Number(e.target.value))}>
                  {deptos.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                </select>
              </label>
              <label style={{ flex: 1, fontSize: '12px' }}>
                Distrito:
                <select value={distritoId} onChange={(e) => setDistritoId(Number(e.target.value))}>
                  {distritosLocal.map((d) => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                </select>
              </label>
              <label style={{ flex: 1, fontSize: '12px' }}>
                Ciudad / Localidad:
                <select value={ciudadId} onChange={(e) => setCiudadId(Number(e.target.value))}>
                  {ciudadesLocal.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                </select>
              </label>
            </div>
          </div>

          {/* Multidivisa y Condiciones */}
          <div className="h-stack" style={{ gap: '1rem', marginTop: '10px' }}>
            <label style={{ flex: 1 }}>
              Condición:
              <select value={condicionOpe} onChange={(e) => setCondicionOpe(Number(e.target.value))}>
                <option value={1}>Contado</option>
                <option value={2}>Crédito</option>
              </select>
            </label>
            {condicionOpe === 2 && (
              <label style={{ flex: 1 }}>Plazo (días) <input value={plazoCredito} onChange={(e) => setPlazoCredito(e.target.value)} /></label>
            )}
            <label style={{ flex: 1 }}>
              Moneda:
              <select value={moneda} onChange={(e) => setMoneda(e.target.value)}>
                <option value="PYG">PYG (Guaraní)</option>
                <option value="USD">USD (Dólar)</option>
                <option value="BRL">BRL (Real)</option>
                <option value="ARS">ARS (Peso Arg.)</option>
                <option value="EUR">EUR (Euro)</option>
              </select>
            </label>
            {moneda !== "PYG" && (
              <label style={{ flex: 1 }}>Tipo Cambio <input type="number" value={tipoCambio} onChange={(e) => setTipoCambio(Number(e.target.value))} /></label>
            )}
          </div>

          {/* Líneas de Detalle */}
          <div className="full lineas" style={{ marginTop: '15px' }}>
            <h4 style={{ margin: '0 0 8px 0' }}>Detalle de Ítems / Servicios:</h4>
            {lineas.map((ln, i) => (
              <div key={i} className="linea-row" style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                <select
                  style={{ width: '160px' }}
                  value={ln.producto_id || ""}
                  onChange={(e) => {
                    const pid = Number(e.target.value);
                    const prod = productos.find(p => p.id === pid);
                    const n = [...lineas];
                    if (prod) {
                      n[i].producto_id = prod.id;
                      n[i].d_cod_int = prod.sku;
                      n[i].d_des_pro_ser = prod.descripcion;
                      n[i].d_p_uni_pro_ser = prod.precio_venta;
                    } else { n[i].producto_id = undefined; }
                    setLineas(n);
                  }}
                >
                  <option value="">Artículo catálogo...</option>
                  {productos.map(p => <option key={p.id} value={p.id}>{p.sku} - {p.descripcion}</option>)}
                </select>
                <input
                  className="grow"
                  placeholder="Descripción"
                  value={ln.d_des_pro_ser}
                  onChange={e => { const n=[...lineas]; n[i].d_des_pro_ser=e.target.value; setLineas(n); }}
                  required
                />
                <input
                  type="number"
                  style={{ width: '70px' }}
                  title="Cantidad"
                  value={ln.d_cant_pro_ser}
                  onChange={e => { const n=[...lineas]; n[i].d_cant_pro_ser=Number(e.target.value); setLineas(n); }}
                  required
                />
                <input
                  type="number"
                  style={{ width: '110px' }}
                  title="Precio Unitario"
                  value={ln.d_p_uni_pro_ser}
                  onChange={e => { const n=[...lineas]; n[i].d_p_uni_pro_ser=Number(e.target.value); setLineas(n); }}
                  required
                />
                <select
                  style={{ width: '85px' }}
                  value={ln.d_tasa_iva}
                  onChange={e => { const n=[...lineas]; n[i].d_tasa_iva=Number(e.target.value); setLineas(n); }}
                >
                  <option value={10}>IVA 10%</option>
                  <option value={5}>IVA 5%</option>
                  <option value={0}>Exento</option>
                </select>
                <input
                  type="number"
                  style={{ width: '80px' }}
                  placeholder="Desc."
                  title="Descuento ítem"
                  value={ln.d_desc_item || 0}
                  onChange={e => { const n=[...lineas]; n[i].d_desc_item=Number(e.target.value); setLineas(n); }}
                />
                <button
                  type="button"
                  style={{ background: '#fee2e2', color: '#991b1b', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}
                  onClick={() => { if (lineas.length > 1) setLineas(lineas.filter((_, idx) => idx !== i)); }}
                >
                  🗑️
                </button>
              </div>
            ))}
            <button
              type="button"
              className="secondary small"
              onClick={() => setLineas([...lineas, { producto_id: undefined, d_cod_int: "ART", d_des_pro_ser: "", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10, d_desc_item: 0 }])}
            >
              ➕ Agregar Ítem
            </button>
          </div>

          {/* Resumen Totales y Descuentos */}
          <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0', marginTop: '15px' }}>
            <div className="h-stack" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                <label style={{ fontSize: '13px' }}>
                  Descuento Global ({moneda}):
                  <input
                    type="number"
                    style={{ width: '100px', marginLeft: '6px' }}
                    value={descuentoGlobal}
                    onChange={(e) => setDescuentoGlobal(Number(e.target.value))}
                  />
                </label>
                {moneda === "PYG" && (
                  <label style={{ fontSize: '13px' }}>
                    Redondeo:
                    <input
                      type="number"
                      style={{ width: '80px', marginLeft: '6px' }}
                      value={redondeo}
                      onChange={(e) => setRedondeo(Number(e.target.value))}
                    />
                  </label>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '13px', color: '#64748b' }}>Subtotal: {moneda} {subtotalBruto.toLocaleString()}</div>
                {totalDescuentos > 0 && <div style={{ fontSize: '13px', color: '#dc2626' }}>Descuentos: -{moneda} {totalDescuentos.toLocaleString()}</div>}
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1e293b', marginTop: '4px' }}>
                  Total a Pagar: {moneda} {totalGeneral.toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          <button type="submit" className="primary full" disabled={loading} style={{ marginTop: '15px', padding: '12px', fontSize: '16px' }}>
            {loading ? "Firmando y Generando..." : `🔐 Firmar y Emitir ${TIPO_DOC_LABEL[tipoDoc] || "Documento"}`}
          </button>
        </form>
      </div>
    </div>
  );
}

const TIPO_DOC_LABEL: Record<number, string> = {
  1: "Factura Electrónica",
  2: "Factura de Exportación",
  4: "Autofactura",
  5: "Nota de Crédito",
  6: "Nota de Débito",
  7: "Nota de Remisión",
};
