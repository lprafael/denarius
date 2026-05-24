import { useState, useEffect } from "react";
import {
  listClientes,
  deleteCliente,
  upsertCliente,
  getDepartamentos,
  getDistritos,
  getBarrios,
  consultarRuc
} from "../api";

interface ClientesViewProps {
  refresh?: () => Promise<void>;
}

export function ClientesView({ refresh }: ClientesViewProps) {
  const [clientes, setClientes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editingCliente, setEditingCliente] = useState<any>(null);

  // Form states
  const [ruc, setRuc] = useState("");
  const [dv, setDv] = useState("");
  const [razonSocial, setRazonSocial] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [direccion, setDireccion] = useState("");
  
  const [deptoId, setDeptoId] = useState<number>(0);
  const [distritoId, setDistritoId] = useState<number>(0);
  const [barrioId, setBarrioId] = useState<number>(0);

  const [deptos, setDeptos] = useState<any[]>([]);
  const [distritosLocal, setDistritosLocal] = useState<any[]>([]);
  const [barriosLocal, setBarriosLocal] = useState<any[]>([]);

  useEffect(() => {
    loadClientes();
    getDepartamentos().then(setDeptos).catch(console.error);
  }, []);

  useEffect(() => {
    async function fetchDistritos() {
      if (deptoId > 0) {
        const d = await getDistritos(deptoId);
        setDistritosLocal(d);
      } else {
        setDistritosLocal([]);
      }
    }
    fetchDistritos();
  }, [deptoId]);

  useEffect(() => {
    async function fetchBarrios() {
      if (deptoId > 0 && distritoId > 0) {
        const b = await getBarrios(deptoId, distritoId);
        setBarriosLocal(b);
      } else {
        setBarriosLocal([]);
      }
    }
    fetchBarrios();
  }, [deptoId, distritoId]);

  async function loadClientes() {
    setLoading(true);
    try {
      const data = await listClientes();
      setClientes(data);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onRucBlur(val: string) {
    if (!val || editingCliente?.id) return; // Only auto-fill for new clients
    
    // Auto-calculate DV
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
    if (!dv) setDv(calcDv);

    if (val.length >= 5) {
      try {
        const res = await consultarRuc(val);
        if (res.ok && res.razon_social) {
          if (!razonSocial) setRazonSocial(res.razon_social);
          if (res.dv && !dv) setDv(res.dv);
        }
      } catch (err) {}
    }
  }

  function openModal(cliente?: any) {
    if (cliente) {
      setEditingCliente(cliente);
      const parts = cliente.ruc_con_dv ? cliente.ruc_con_dv.split('-') : ["", ""];
      setRuc(parts[0]);
      setDv(parts[1] || "");
      setRazonSocial(cliente.razon_social || "");
      setEmail(cliente.email || "");
      setTelefono(cliente.telefono || "");
      setDireccion(cliente.direccion || "");
      setDeptoId(cliente.c_dep || 0);
      setDistritoId(cliente.c_ciu || 0);
      setBarrioId(cliente.c_bar || 0);
    } else {
      setEditingCliente(null);
      setRuc("");
      setDv("");
      setRazonSocial("");
      setEmail("");
      setTelefono("");
      setDireccion("");
      setDeptoId(0);
      setDistritoId(0);
      setBarrioId(0);
    }
    setShowModal(true);
  }

  async function onSave() {
    if (!ruc || !razonSocial) {
      alert("RUC y Razón Social son obligatorios.");
      return;
    }
    setLoading(true);
    try {
      await upsertCliente({
        ruc_con_dv: `${ruc}-${dv}`,
        razon_social: razonSocial,
        email: email,
        telefono: telefono,
        direccion: direccion,
        c_dep: deptoId || 1, // Defaulting to CAPITAL if 0 to avoid SIFEN errors
        d_des_dep: deptos.find(d => d.id === deptoId)?.nombre || "CAPITAL",
        c_ciu: distritoId || 1,
        d_des_ciu: distritosLocal.find(d => d.id === distritoId)?.nombre || "ASUNCION (DISTRITO)",
        c_bar: barrioId || 1,
        d_des_bar: barriosLocal.find(b => b.id === barrioId)?.nombre || ""
      });
      setShowModal(false);
      await loadClientes();
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("¿Estás seguro de eliminar este cliente?")) return;
    setLoading(true);
    try {
      await deleteCliente(id);
      await loadClientes();
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card wide">
      {err && <div className="alert">{err}</div>}
      <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
        <h2>Gestión de Clientes</h2>
        <button className="primary" onClick={() => openModal()}>+ Nuevo Cliente</button>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>RUC</th>
            <th>Razón Social</th>
            <th>Email</th>
            <th>Teléfono</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {clientes.length === 0 ? (
            <tr><td colSpan={5} style={{textAlign:'center', padding:'2rem', opacity:0.5}}>No hay clientes registrados.</td></tr>
          ) : (
            clientes.map(c => (
              <tr key={c.id}>
                <td className="mono">{c.ruc_con_dv}</td>
                <td>{c.razon_social}</td>
                <td>{c.email}</td>
                <td>{c.telefono}</td>
                <td>
                  <button className="linkish" onClick={() => openModal(c)}>✏️</button>
                  {" | "}
                  <button className="linkish danger" onClick={() => onDelete(c.id)}>🗑️</button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '600px', background:'var(--panel)', padding:'2rem', borderRadius:'12px'}}>
            <h2>{editingCliente ? "Editar Cliente" : "Nuevo Cliente"}</h2>
            <div className="form">
              <div className="h-stack" style={{gap:'1rem'}}>
                <label style={{flex:2}}>RUC <input value={ruc} onChange={e=>setRuc(e.target.value)} onBlur={e=>onRucBlur(e.target.value)} disabled={!!editingCliente} /></label>
                <label style={{flex:1}}>DV <input value={dv} onChange={e=>setDv(e.target.value)} disabled={!!editingCliente} /></label>
              </div>
              <label className="full">Razón Social <input value={razonSocial} onChange={e => setRazonSocial(e.target.value)} /></label>
              
              <div className="h-stack" style={{gap:'1rem'}}>
                <label style={{flex:1}}>Email <input type="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
                <label style={{flex:1}}>Teléfono <input value={telefono} onChange={e => setTelefono(e.target.value)} /></label>
              </div>

              <label className="full">Dirección <input value={direccion} onChange={e => setDireccion(e.target.value)} /></label>

              <div className="h-stack" style={{gap:'1rem'}}>
                <label style={{flex:1}}>Departamento
                  <select value={deptoId} onChange={e => setDeptoId(Number(e.target.value))}>
                    <option value={0}>Seleccione...</option>
                    {deptos.map(d => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                  </select>
                </label>
                <label style={{flex:1}}>Distrito
                  <select value={distritoId} onChange={e => setDistritoId(Number(e.target.value))} disabled={deptoId === 0}>
                    <option value={0}>Seleccione...</option>
                    {distritosLocal.map(d => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                  </select>
                </label>
              </div>
              
              <label className="full">Barrio
                <select value={barrioId} onChange={e => setBarrioId(Number(e.target.value))} disabled={distritoId === 0}>
                  <option value={0}>Seleccione...</option>
                  {barriosLocal.map(b => <option key={b.id} value={b.id}>{b.nombre}</option>)}
                </select>
              </label>

              <div className="h-stack" style={{marginTop: '1.5rem', gap: '1rem'}}>
                <button className="secondary full" onClick={() => setShowModal(false)} disabled={loading}>Cancelar</button>
                <button className="primary full" onClick={onSave} disabled={loading || !ruc || !razonSocial}>
                  {loading ? "Guardando..." : "Guardar Cliente"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
