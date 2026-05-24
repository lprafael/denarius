import React, { useState, useEffect } from "react";
import {
  createFactura,
  consultarRuc,
  getClienteByRuc,
  upsertCliente,
  getDepartamentos,
  getDistritos,
  getBarrios,
  type FacturaCreate,
} from "../api";

interface FacturacionViewProps {
  emisor: any;
  productos: any[];
  refresh: () => Promise<void>;
  // For budget to invoice mapping
  initialFacturaParams: any;
}

export function FacturacionView({ emisor, productos, refresh, initialFacturaParams }: FacturacionViewProps) {
  const [ruc, setRuc] = useState(initialFacturaParams?.ruc || "");
  const [dv, setDv] = useState(initialFacturaParams?.dv || "");
  const [nombre, setNombre] = useState(initialFacturaParams?.nombre || "");
  const [clienteEmail, setClienteEmail] = useState(initialFacturaParams?.clienteEmail || "");
  const [clienteTel, setClienteTel] = useState(initialFacturaParams?.clienteTel || "");
  const [clienteDir, setClienteDir] = useState(initialFacturaParams?.clienteDir || "");
  const [deptoId, setDeptoId] = useState<number>(0);
  const [distritoId, setDistritoId] = useState<number>(0);
  const [barrioId, setBarrioId] = useState<number>(0);
  const [lineas, setLineas] = useState<any[]>(
    initialFacturaParams?.lineas?.length > 0 
      ? initialFacturaParams.lineas 
      : [{ producto_id: undefined, d_cod_int: "ART001", d_des_pro_ser: "Producto o servicio", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10 }]
  );

  const [clienteEncontrado, setClienteEncontrado] = useState<any>(null);
  const [showClienteModal, setShowClienteModal] = useState<boolean>(false);
  const [deptos, setDeptos] = useState<any[]>([]);
  const [distritosLocal, setDistritosLocal] = useState<any[]>([]);
  const [barriosLocal, setBarriosLocal] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // Update when initialFacturaParams changes
  useEffect(() => {
    if (initialFacturaParams) {
      setRuc(initialFacturaParams.ruc || "");
      setDv(initialFacturaParams.dv || "");
      setNombre(initialFacturaParams.nombre || "");
      setClienteEmail(initialFacturaParams.clienteEmail || "");
      setClienteTel(initialFacturaParams.clienteTel || "");
      setClienteDir(initialFacturaParams.clienteDir || "");
      if (initialFacturaParams.lineas?.length > 0) {
        setLineas(initialFacturaParams.lineas);
      }
    }
  }, [initialFacturaParams]);

  useEffect(() => {
    getDepartamentos().then(setDeptos).catch(console.error);
  }, []);

  useEffect(() => {
    async function fetchDistritos() {
      if (deptoId > 0) {
        const d = await getDistritos(deptoId);
        setDistritosLocal(d);
      }
    }
    fetchDistritos();
  }, [deptoId]);

  useEffect(() => {
    async function fetchBarrios() {
      if (deptoId > 0 && distritoId > 0) {
        const b = await getBarrios(deptoId, distritoId);
        setBarriosLocal(b);
      }
    }
    fetchBarrios();
  }, [deptoId, distritoId]);

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
        if (cli.c_ciu) setDistritoId(cli.c_ciu);
        if (cli.c_bar) setBarrioId(cli.c_bar);
        setDv(cli.ruc_con_dv.split('-')[1] || calcDv);
        setClienteEncontrado(cli);
        return;
      } else {
        setClienteEncontrado(null);
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

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setErr("");
    try {
      const payload: FacturaCreate = {
        receptor_ruc: ruc,
        receptor_dv: dv,
        receptor_nombre: nombre,
        receptor_tel: clienteTel,
        receptor_dir: clienteDir,
        lineas: lineas.map((l) => ({
          producto_id: l.producto_id,
          d_cod_int: l.d_cod_int,
          d_des_pro_ser: l.d_des_pro_ser,
          d_cant_pro_ser: Number(l.d_cant_pro_ser),
          d_p_uni_pro_ser: Math.round(Number(l.d_p_uni_pro_ser)),
          d_tasa_iva: Number(l.d_tasa_iva),
        })),
      };
      await createFactura(payload);
      try {
        await upsertCliente({
          ruc_con_dv: `${ruc}-${dv}`,
          razon_social: nombre,
          email: clienteEmail,
          telefono: clienteTel,
          direccion: clienteDir,
          c_dep: deptoId,
          d_des_dep: deptos.find(d => d.id === deptoId)?.nombre || "",
          c_ciu: distritoId,
          d_des_ciu: distritosLocal.find(d => d.id === distritoId)?.nombre || "",
          c_bar: barrioId,
          d_des_bar: barriosLocal.find(b => b.id === barrioId)?.nombre || ""
        });
      } catch (err) {}
      setRuc(""); setNombre(""); setLineas([{ producto_id: undefined, d_cod_int: "", d_des_pro_ser: "", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10 }]);
      await refresh();
      alert("Factura emitida");
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid">
      {err && <div className="alert">{err}</div>}
      <div className="card wide">
        <h2>Emisor Actual</h2>
        {emisor && (
          <dl className="dl">
            <dt>RUC</dt><dd>{emisor.ruc_con_dv}</dd>
            <dt>Razón</dt><dd>{emisor.razon_social}</dd>
          </dl>
        )}
      </div>
      <div className="card wide">
        <h2>Emisión Factura Electrónica</h2>
        <form onSubmit={onSubmit} className="form">
          <div className="h-stack" style={{gap:'1rem'}}>
            <label style={{flex:2}}>RUC <input value={ruc} onChange={e=>setRuc(e.target.value)} onBlur={e=>onRucBlur(e.target.value)} /></label>
            <label style={{flex:1}}>DV <input value={dv} onChange={e=>setDv(e.target.value)} /></label>
          </div>

          {clienteEncontrado && !clienteEncontrado._is_new_sifen ? (
            <div className="alert success small h-stack" style={{justifyContent: 'space-between', padding: '0.5rem 1rem', marginTop: '0.5rem', marginBottom: '0.5rem'}}>
              <span>✅ Cliente Registrado en BBDD</span>
              <button type="button" className="secondary small" onClick={() => setShowClienteModal(true)}>Actualizar Datos</button>
            </div>
          ) : clienteEncontrado?._is_new_sifen ? (
            <div className="alert info small h-stack" style={{justifyContent: 'space-between', padding: '0.5rem 1rem', marginTop: '0.5rem', marginBottom: '0.5rem'}}>
              <span>ℹ️ RUC Válido (SIFEN) - No registrado localmente</span>
              <button type="button" className="secondary small" onClick={() => setShowClienteModal(true)}>Agregar a Base de Datos</button>
            </div>
          ) : ruc && ruc.length >= 5 ? (
            <div className="alert warning small h-stack" style={{justifyContent: 'space-between', padding: '0.5rem 1rem', marginTop: '0.5rem', marginBottom: '0.5rem'}}>
              <span>⚠️ Cliente no encontrado en SIFEN ni localmente</span>
              <button type="button" className="secondary small" onClick={() => setShowClienteModal(true)}>Agregar Manualmente</button>
            </div>
          ) : null}

          <label className="full">Nombre / Razón Social <input value={nombre} onChange={e=>setNombre(e.target.value)} /></label>
          <label className="full">Dirección <input value={clienteDir} onChange={e=>setClienteDir(e.target.value)} /></label>
          <div className="full lineas">
            {lineas.map((ln, i) => (
              <div key={i} className="linea-row" style={{display:'flex', gap:'8px', marginBottom:'8px'}}>
                <select
                  style={{ width: '150px' }}
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
                  <option value="">Articulo...</option>
                  {productos.map(p => <option key={p.id} value={p.id}>{p.sku} - {p.descripcion}</option>)}
                </select>
                <input className="grow" value={ln.d_des_pro_ser} onChange={e => { const n=[...lineas]; n[i].d_des_pro_ser=e.target.value; setLineas(n); }} />
                <input type="number" style={{width:'60px'}} value={ln.d_cant_pro_ser} onChange={e => { const n=[...lineas]; n[i].d_cant_pro_ser=Number(e.target.value); setLineas(n); }} />
                <input type="number" style={{width:'100px'}} value={ln.d_p_uni_pro_ser} onChange={e => { const n=[...lineas]; n[i].d_p_uni_pro_ser=Number(e.target.value); setLineas(n); }} />
              </div>
            ))}
            <button type="button" className="secondary small" onClick={()=>setLineas([...lineas, {producto_id:undefined, d_cod_int:"", d_des_pro_ser:"", d_cant_pro_ser:1, d_p_uni_pro_ser:0, d_tasa_iva:10}])}>+ Línea</button>
          </div>
          <button type="submit" className="primary full" disabled={loading}>Firmar y Emitir SIFEN</button>
        </form>
      </div>

      {showClienteModal && (
        <div className="modal-overlay" onClick={() => setShowClienteModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '500px', background:'var(--panel)', padding:'2rem', borderRadius:'12px'}}>
            <h2>Ficha de Cliente</h2>
            <div className="form">
              <label className="full">RUC <input value={`${ruc}-${dv}`} disabled /></label>
              <label className="full">Razón Social <input value={nombre} onChange={e => setNombre(e.target.value)} /></label>
              <label>Email <input value={clienteEmail} onChange={e => setClienteEmail(e.target.value)} /></label>
              <label>Teléfono <input value={clienteTel} onChange={e => setClienteTel(e.target.value)} /></label>
              <label className="full">Dirección <input value={clienteDir} onChange={e => setClienteDir(e.target.value)} /></label>
              
              <div className="h-stack" style={{marginTop: '1.5rem', gap: '1rem'}}>
                <button className="secondary full" onClick={() => setShowClienteModal(false)}>Cancelar</button>
                <button 
                  className="primary full" 
                  onClick={async () => {
                    setLoading(true);
                    try {
                      await upsertCliente({
                        ruc_con_dv: `${ruc}-${dv}`,
                        razon_social: nombre,
                        email: clienteEmail,
                        telefono: clienteTel,
                        direccion: clienteDir,
                        c_dep: deptoId,
                        d_des_dep: deptos.find(d => d.id === deptoId)?.nombre || "",
                        c_ciu: distritoId,
                        d_des_ciu: distritosLocal.find(d => d.id === distritoId)?.nombre || "",
                        c_bar: barrioId,
                        d_des_bar: barriosLocal.find(b => b.id === barrioId)?.nombre || ""
                      });
                      setClienteEncontrado({ _is_new_sifen: false });
                      setShowClienteModal(false);
                      alert("Cliente guardado correctamente");
                    } catch (e) {
                      setErr(String(e));
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading || !ruc || !nombre}
                >Guardar Datos</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
