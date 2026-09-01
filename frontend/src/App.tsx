import { useCallback, useEffect, useRef, useState } from "react";
declare global { interface Window { google: any } }

import logo from "./assets/logo.png";
import {
  getEmisor,
  getHealth,
  getXml,
  getKudeHtml,
  login,
  listFacturas,
  listEmpresasGlobal,
  toggleEmpresa,
  deleteEmpresa,
  updateEmpresa,
  getAdminDashboard,

  createSuperAdmin,

  downloadDoc,
  registrarEmpresa,
  restoreAccessToken,
  setAccessToken,
  googleLogin,
  listEquipos,
  updateEquipo,
  deleteEquipo,
  updateEmisor,
  listProductos,
  listCompras,
  getProyeccionIva,
  getStatsVentas,
  getTopProductos,
  listUsuarios,
  type EmisorOut,

  type FacturaOut,
  updateAdminEmail,
  resetAdminPassword,
  listAuditoria,
  type AuditLogOut
} from "./api";
import { PresupuestosView } from "./views/PresupuestosView";
import { FacturacionView } from "./views/FacturacionView";
import { InventarioView } from "./views/InventarioView";
import { ComprasView } from "./views/ComprasView";
import { UsuariosView } from "./views/UsuariosView";
import { ClientesView } from "./views/ClientesView";
import { LotesView } from "./views/LotesView";


export function App() {
  const [authed, setAuthed] = useState<boolean>(false);

  const [usuarioRol, setUsuarioRol] = useState<string>("operador");
  const [usuarioEmail, setUsuarioEmail] = useState<string>("");
  const [empresaNombre, setEmpresaNombre] = useState<string>("");
  const [health, setHealth] = useState<string>("");
  const [emisor, setEmisor] = useState<EmisorOut | null>(null);
  const [facturas, setFacturas] = useState<FacturaOut[]>([]);
  const [empresas, setEmpresas] = useState<any[]>([]);
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPass, setAdminPass] = useState("");
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [previewImg, setPreviewImg] = useState<string | null>(null);
  const [showCertGuide, setShowCertGuide] = useState<boolean>(false);
  const [editEmpresa, setEditEmpresa] = useState<any>(null);
  const [editFields, setEditFields] = useState({ 
    nombre: "", 
    razon_social: "", 
    ruc_con_dv: "", 
    plantilla_kude: "",
    restriccion_equipos: false,
    max_equipos: 0,
    email_admin: ""
  });

  const [cscId, setCscId] = useState("");
  const [cscSec, setCscSec] = useState("");
  const [dashboard, setDashboard] = useState<any | null>(null);
  const [adminActiveTab, setAdminActiveTab] = useState<"stats" | "facturas">("stats");
  const [adminFacturaEmpresaId, setAdminFacturaEmpresaId] = useState<number | undefined>();
  const [adminEmpresaNombre, setAdminEmpresaNombre] = useState<string>("");

  const [deviceId, setDeviceId] = useState<string>("");
  const [equipos, setEquipos] = useState<any[]>([]);
  const [showEquiposModal, setShowEquiposModal] = useState(false);


  const [loginEmail, setLoginEmail] = useState("");
  const [loginPass, setLoginPass] = useState("");
  const [regEmpresa, setRegEmpresa] = useState("");
  const [regRuc, setRegRuc] = useState("");
  const [regRazon, setRegRazon] = useState("");
  const [regGoogleToken, setRegGoogleToken] = useState<string | null>(null);
  const [regEmail, setRegEmail] = useState("");
  const [regPass, setRegPass] = useState("");
  
  const googleInitialized = useRef(false);

  const [activeTab, setActiveTab] = useState<"dashboard" | "factura" | "inventario" | "compras" | "usuarios" | "config" | "presupuestos" | "auditoria" | "clientes">("dashboard");
  const [productos, setProductos] = useState<any[]>([]);
  const [compras, setCompras] = useState<any[]>([]);
  const [usuariosEmpresa, setUsuariosEmpresa] = useState<any[]>([]);
  const [proyeccionIva, setProyeccionIva] = useState<any | null>(null);
  const [statsVentas, setStatsVentas] = useState<any[]>([]);
  const [topProductos, setTopProductos] = useState<any[]>([]);
  const [auditoriaLogs, setAuditoriaLogs] = useState<AuditLogOut[]>([]);
  
  // State for bridging Presupuestos -> Facturacion
  const [facturaInitParams, setFacturaInitParams] = useState<any>(null);

  const isCompanyAdmin = usuarioRol?.toLowerCase().includes("admin") && usuarioRol?.toLowerCase() !== "superadmin";

  const logout = useCallback(() => {
    setAccessToken(""); setAuthed(false);
    setEmpresaNombre(""); setEmisor(null);
    setFacturas([]);
    localStorage.removeItem("denarius_rol");
    localStorage.removeItem("denarius_empresa");
    localStorage.removeItem("denarius_email");
  }, []);

  const refresh = useCallback(async () => {
    setErr("");
    try {
      const h = await getHealth();
      setHealth(`${h.nombre}: conexión correcta`);
      if (!authed) return;

      if (usuarioRol === "superadmin") {
        const emps = await listEmpresasGlobal();
        setEmpresas(emps);
        const dash = await getAdminDashboard();
        setDashboard(dash);
        if (adminActiveTab === "facturas") {
           const audit = await listAuditoria(adminFacturaEmpresaId);
           setAuditoriaLogs(audit);
        }
      } else {
        const e = await getEmisor();
        setEmisor(e);
        setCscSec(e.csc_secreto || "");
        setCscId(e.id_csc || "");
        const l = await listFacturas();
        setFacturas(l);
        
        const prods = await listProductos();
        setProductos(prods);
        const comp = await listCompras();
        setCompras(comp);
        const proyect = await getProyeccionIva();
        setProyeccionIva(proyect);
        const sv = await getStatsVentas();
        setStatsVentas(sv);
        const stp = await getTopProductos();
        setTopProductos(stp);

        if (isCompanyAdmin) {
            const listU = await listUsuarios();
            setUsuariosEmpresa(listU);
        }


      }
    } catch (ex: any) {
      console.error("Refresh error:", ex);
      const msg = String(ex);
      if (msg.includes("Signature has expired") || msg.includes("Token inválido")) {
           logout();
      } else {
           setErr(msg);
      }
    }
  }, [authed, usuarioRol, adminActiveTab, adminFacturaEmpresaId, logout, isCompanyAdmin]);



  useEffect(() => {
    let d = localStorage.getItem("denarius_device_id");
    if (!d) {
      d = "dev-" + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
      localStorage.setItem("denarius_device_id", d);
    }
    setDeviceId(d);

    const token = restoreAccessToken();
    const savedRol = localStorage.getItem("denarius_rol");
    const savedEmp = localStorage.getItem("denarius_empresa");
    const savedEmail = localStorage.getItem("denarius_email");
    if (token) {
      setAuthed(true);
      if (savedRol) {
          let norm = savedRol.toLowerCase();
          if (norm.includes("admin") && norm !== "superadmin") norm = "admin";
          setUsuarioRol(norm);
      }
      if (savedEmp) setEmpresaNombre(savedEmp);
      if (savedEmail) setUsuarioEmail(savedEmail);
    }
  }, []);

  useEffect(() => {
    if (authed) refresh();
  }, [authed, refresh]);


  useEffect(() => {
    if (!window.google) return;
    if (!googleInitialized.current) {
        window.google.accounts.id.initialize({
          client_id: "721727768822-772772772.apps.googleusercontent.com", 
          callback: handleGoogleLogin,
          use_fedcm_for_prompt: true,
        });
        googleInitialized.current = true;
    }
    if (!authed) {
      const btn = document.getElementById("google-login-btn");
      if (btn) window.google.accounts.id.renderButton(btn, { theme: "outline", size: "large", width: 250 });
      window.google.accounts.id.prompt();
    }
    const regBtn = document.getElementById("reg-google-btn");
    if (regBtn) window.google.accounts.id.renderButton(regBtn, { theme: "outline", size: "large", text: "signup_with" });
  }, [authed]);


  async function handleGoogleLogin(response: any) {
    setErr("");
    setLoading(true);
    try {
      if (regEmpresa || regRuc || regRazon) {
          setRegGoogleToken(response.credential);
          try {
            const payload = JSON.parse(atob(response.credential.split('.')[1]));
            if (payload.email) setRegEmail(payload.email);
            if (payload.name && !regRazon) setRegRazon(payload.name);
          } catch(e){}
          setLoading(false);
          return;
      }
      const out = await googleLogin(response.credential, deviceId);
      setEmpresaNombre(out.empresa_nombre);
      setUsuarioEmail(out.usuario_email);
      let norm = out.rol.toLowerCase();
      if (norm.includes("admin") && norm !== "superadmin") norm = "admin";
      setUsuarioRol(norm);
      localStorage.setItem("denarius_rol", norm);
      localStorage.setItem("denarius_empresa", out.empresa_nombre);
      localStorage.setItem("denarius_email", out.usuario_email);
      setAuthed(true);
      await refresh();
    } catch (ex: any) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  const loadEquipos = useCallback(async () => {
    try {
      const list = await listEquipos();
      setEquipos(list);
    } catch (e) {
      setErr(String(e));
    }
  }, []);



  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const out = await login(loginEmail, loginPass, deviceId);
      setEmpresaNombre(out.empresa_nombre);
      setUsuarioEmail(out.usuario_email);
      let norm = out.rol.toLowerCase();
      if (norm.includes("admin") && norm !== "superadmin") norm = "admin";
      setUsuarioRol(norm);
      localStorage.setItem("denarius_rol", norm);
      localStorage.setItem("denarius_empresa", out.empresa_nombre);
      localStorage.setItem("denarius_email", out.usuario_email);
      setAuthed(true);
      await refresh();
    } catch (ex: any) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      if (!regGoogleToken && (!regEmail || !regPass)) {
          throw new Error("Debe ingresar email/password o vincular su cuenta de Google.");
      }
      await registrarEmpresa({
        nombre: regEmpresa,
        email_admin: regEmail,
        password_admin: regPass || undefined,
        ruc_con_dv: regRuc,
        razon_social: regRazon,
        google_token: regGoogleToken || undefined
      });
      alert("Solicitud enviada exitosamente. El SuperAdmin revisará su alta.");
      setRegEmpresa(""); setRegRuc(""); setRegRazon(""); setRegEmail(""); setRegPass(""); setRegGoogleToken(null);
    } catch (ex: any) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }



  async function downloadXml(id: number) {
    try {
      const xml = await getXml(id);
      const blob = new Blob([xml], { type: "application/xml;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = `Denarius_DE_${id}.xml`;
      a.click(); URL.revokeObjectURL(a.href);
    } catch (ex) { setErr(String(ex)); }
  }

  async function openKude(id: number) {
    try {
      const html = await getKudeHtml(id);
      const blob = new Blob([html], { type: "text/html;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch (ex) { setErr(String(ex)); }
  }

  async function onToggleEmpresa(id: number) {
    try {
      await toggleEmpresa(id);
      await refresh();
    } catch (e) { setErr(String(e)); }
  }

  function onEditClick(emp: any) {
    setEditEmpresa(emp);
    setEditFields({
      nombre: emp.nombre || "", razon_social: emp.razon_social || "", ruc_con_dv: emp.ruc || "",
      plantilla_kude: emp.plantilla_kude || "kude_ticket.html",
      restriccion_equipos: !!emp.restriccion_equipos, max_equipos: emp.max_equipos || 0,
      email_admin: emp.email_admin || ""
    });
  }

  async function handleResetPassword() {
    if (!editEmpresa) return;
    try {
      setLoading(true);
      await resetAdminPassword(editEmpresa.id, editFields.email_admin);
      alert("Email de reset enviado a: " + editFields.email_admin);
    } catch(e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onSaveEmailAdmin() {
    if (!editEmpresa) return;
    try {
      setLoading(true);
      await updateAdminEmail(editEmpresa.id, editFields.email_admin);
      alert("Email actualizado exitosamente");
      await refresh();
    } catch(e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onToggleEquipo(id: number, current: boolean) {
    try {
      await updateEquipo(id, { autorizado: !current });
      await loadEquipos();
    } catch (e) { setErr(String(e)); }
  }

  async function onDeleteEquipo(id: number) {
    if (!window.confirm("¿Eliminar?")) return;
    try {
      await deleteEquipo(id);
      await loadEquipos();
    } catch (e) { setErr(String(e)); }
  }

  async function onSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editEmpresa) return;
    setLoading(true);
    try {
      await updateEmpresa(editEmpresa.id, editFields);
      setEditEmpresa(null);
      await refresh();
    } catch (e) { setErr(String(e)); } finally { setLoading(false); }
  }

  async function onAddAdmin(e: React.FormEvent) {
    e.preventDefault(); setLoading(true);
    try {
      await createSuperAdmin(adminName, adminEmail, adminPass);
      alert("Admin creado");
      setAdminName(""); setAdminEmail(""); setAdminPass("");
    } catch (ex) { setErr(String(ex)); } finally { setLoading(false); }
  }

  async function onDownloadManual(filename: string) {
    try {
      const blob = await downloadDoc(filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url);
    } catch (e) { setErr(String(e)); }
  }



  async function onUpdateEmisorConfig() {
    setLoading(true);
    try {
      const updated = await updateEmisor({ id_csc: cscId, csc_secreto: cscSec });
      setEmisor(updated); alert("Actualizado");
    } catch (e) { setErr(String(e)); } finally { setLoading(false); }
  }

  function handleFacturarPresupuesto(p: any) {
    const rucParts = p.cliente_ruc ? p.cliente_ruc.split('-') : ["", ""];
    
    const newLineas: any[] = [];
    if (p.grupos) {
        p.grupos.forEach((g: any) => {
            if (g.conceptos) {
                g.conceptos.forEach((c: any) => {
                    const prodMatch = productos.find(prod => prod.descripcion.toLowerCase() === c.descripcion.toLowerCase());
                    newLineas.push({
                        producto_id: prodMatch ? prodMatch.id : undefined,
                        d_cod_int: prodMatch ? prodMatch.sku : "",
                        d_des_pro_ser: c.descripcion,
                        d_cant_pro_ser: c.cantidad,
                        d_p_uni_pro_ser: c.precio_unitario,
                        d_tasa_iva: c.tasa_iva
                    });
                });
            }
        });
    }

    setFacturaInitParams({
      ruc: rucParts[0],
      dv: rucParts[1] || "",
      nombre: p.cliente_nombre || "",
      clienteDir: p.cliente_direccion || "",
      clienteTel: p.cliente_telefono || "",
      clienteEmail: p.cliente_email || "",
      lineas: newLineas
    });
    
    setActiveTab("factura");
  }


  return (
    <div className="layout">
      <header className="hero">
        <div className="brand-container">
          <img src={logo} alt="Denarius Logo" className="main-logo" onClick={() => setPreviewImg(logo)} />
          <h1>Denarius(by Aurelius)</h1>
        </div>
        <p className="eyebrow">Paraguay · SIFEN · e-Kuatia</p>
        <p className="lede">Innovación en Facturación Electrónica y Gestión de Stock.</p>
        <p className="status">{health}</p>
        {authed && (
          <p className="status">
            Sesión {(usuarioRol ?? "operador").toUpperCase()} - {empresaNombre} ·{" "}
            <button className="linkish" onClick={logout}>cerrar sesión</button>
          </p>
        )}
      </header>

      {authed && usuarioRol?.toLowerCase() !== "superadmin" && (
        <nav className="tab-nav">
          <button className={activeTab === "dashboard" ? "active" : ""} onClick={() => setActiveTab("dashboard")}>Dashboard</button>
          <button className={activeTab === "factura" ? "active" : ""} onClick={() => setActiveTab("factura")}>Emitir</button>
          <button className={activeTab === "inventario" ? "active" : ""} onClick={() => setActiveTab("inventario")}>📦 Productos/Servicios</button>
          <button className={activeTab === "clientes" ? "active" : ""} onClick={() => setActiveTab("clientes")}>👥 Clientes</button>
          <button className={activeTab === "compras" ? "active" : ""} onClick={() => setActiveTab("compras")}>📥 Compras SIFEN</button>
          <button className={activeTab === "lotes" ? "active" : ""} onClick={() => setActiveTab("lotes")}>📦 Lotes SIFEN</button>
          <button className={activeTab === "presupuestos" ? "active" : ""} onClick={() => setActiveTab("presupuestos")}>Presupuestos</button>
          {isCompanyAdmin && (
            <button className={activeTab === "usuarios" ? "active" : ""} onClick={() => setActiveTab("usuarios")}>Usuarios</button>
          )}
          <button className={activeTab === "config" ? "active" : ""} onClick={() => setActiveTab("config")}>🔑</button>
        </nav>
      )}

      {err && <div className="alert">{err}</div>}

      {authed && usuarioRol?.toLowerCase() === "superadmin" && (
        <main className="content">
            <section className="card wide dashboard-summary">
                <div className="dashboard-header h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
                    <h2>Panel Global (SuperAdmin)</h2>
                    <div className="tabs h-stack">
                        <button className={adminActiveTab==='stats'?'primary':'secondary'} onClick={()=>setAdminActiveTab('stats')}>Dashboard</button>
                        <button className={adminActiveTab==='facturas'?'primary':'secondary'} onClick={()=>setAdminActiveTab('facturas')}>Auditoría</button>
                    </div>
                </div>

                {adminActiveTab === 'stats' ? (
                    <>
                    <div className="stats-grid">
                        <div className="card stat-card primary"><span>Total Empresas</span><span>{dashboard?.total_empresas}</span></div>
                        <div className="card stat-card success"><span>Empresas Activas</span><span>{dashboard?.empresas_activas}</span></div>
                        <div className="card stat-card secondary"><span>Facturas Emitidas</span><span>{dashboard?.total_facturas}</span></div>
                        <div className="card stat-card highlight"><span>Volumen Operado</span><span>Gs. {dashboard?.monto_total_general?.toLocaleString()}</span></div>
                    </div>

                    <h3 style={{marginTop:'2rem'}}>Empresas Registradas</h3>
                    <table className="table">
                        <thead><tr><th>ID</th><th>Nombre</th><th>RUC</th><th>Estado</th><th>Acciones</th></tr></thead>
                        <tbody>
                            {dashboard?.detalle_empresas?.map((d:any) => (
                                <tr key={d.empresa_id}>
                                    <td>{d.empresa_id}</td>
                                    <td><strong>{d.nombre}</strong></td>
                                    <td>{d.ruc}</td>
                                    <td><span className={`badge ${d.estado}`}>{d.estado.toUpperCase()}</span></td>
                                    <td>
                                        <button className="linkish" onClick={() => { const full = empresas.find(e => e.id===d.empresa_id); if(full) onEditClick(full); }}>✏️</button>
                                        {" | "}
                                        <button className="linkish" onClick={() => onToggleEmpresa(d.empresa_id)}>
                                            {d.estado === 'activo' ? '🚫' : '✅'}
                                        </button>
                                        {" | "}
                                        <button className="linkish" onClick={async () => {
                                            if (window.confirm('¿Eliminar empresa?')) {
                                                await deleteEmpresa(d.empresa_id);
                                                await refresh();
                                            }
                                        }}>🗑️</button>
                                        {" | "}
                                        <button className="linkish" onClick={async () => {
                                            setAdminFacturaEmpresaId(d.empresa_id);
                                            setAdminEmpresaNombre(d.nombre);
                                            setAdminActiveTab("facturas");
                                            const audit = await listAuditoria(d.empresa_id);
                                            setAuditoriaLogs(audit);
                                        }}>👁️</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    </>
                ) : (
                    <>
                    <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1rem'}}>
                        <h3>Auditando: {adminEmpresaNombre || "Global"}</h3>
                        <button className="linkish" onClick={async () => { setAdminFacturaEmpresaId(undefined); setAdminEmpresaNombre("Global"); setLoading(true); try{ const l = await listAuditoria(); setAuditoriaLogs(l); }finally{setLoading(false);} }}>Limpiar Filtro</button>
                    </div>
                    <table className="table">
                        <thead><tr><th>ID</th><th>Fecha</th><th>Empresa ID</th><th>Usuario ID</th><th>Acción</th><th>Detalle</th><th>IP</th></tr></thead>
                        <tbody>
                            {auditoriaLogs.map(a => (
                                <tr key={a.id}>
                                    <td>{a.id}</td>
                                    <td>{new Date(a.created_at).toLocaleString()}</td>
                                    <td>{a.empresa_id || "-"}</td>
                                    <td>{a.usuario_id || "-"}</td>
                                    <td><span className="badge info">{a.accion}</span></td>
                                    <td>{a.detalle || "-"}</td>
                                    <td>{a.ip}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    </>
                )}
            </section>

            <div className="grid">
                <section className="card">
                    <h2>Nuevo SuperAdmin</h2>
                    <form onSubmit={onAddAdmin} className="form">
                        <label className="full">Nombre <input value={adminName} onChange={e=>setAdminName(e.target.value)} /></label>
                        <label className="full">Email <input value={adminEmail} onChange={e=>setAdminEmail(e.target.value)} /></label>
                        <label className="full">Pass <input type="password" value={adminPass} onChange={e=>setAdminPass(e.target.value)} /></label>
                        <button type="submit" className="primary full">Crear</button>
                    </form>
                </section>

                <section className="card">
                    <h2>Manuales Técnicos</h2>
                    <p className="hint">Documentación oficial para administración y cumplimiento.</p>
                    <div className="v-stack" style={{gap:'10px', marginTop:'1rem'}}>
                        <button className="secondary" onClick={() => onDownloadManual("MANUAL_USUARIO.md")}>📖 Manual de Usuario</button>
                        <button className="secondary" onClick={() => onDownloadManual("MANUAL_TECNICO.md")}>🛠️ Manual Técnico</button>
                    </div>
                </section>
            </div>
        </main>
      )}

      {authed && usuarioRol?.toLowerCase() !== "superadmin" && (
        <main className="content">
            {activeTab === "dashboard" && (
                <section className="dashboard-v3">
                    <div className="stats-grid">
                        <div className="card stat-card primary"><span>IVA Ventas</span><span>{proyeccionIva?.iva_debito_ventas?.toLocaleString()}</span></div>
                        <div className="card stat-card secondary"><span>IVA Compras</span><span>{proyeccionIva?.iva_credito_compras?.toLocaleString()}</span></div>
                        <div className="card stat-card success"><span>A Pagar</span><span>{proyeccionIva?.iva_estimado_pagar?.toLocaleString()}</span></div>
                    </div>
                    <div className="grid">
                        <div className="card wide">
                            <h3>Ventas Diarias (Últimos 30 días)</h3>
                            <div style={{ height: '150px', display: 'flex', alignItems: 'flex-end', gap: '4px', padding: '1rem' }}>
                                {statsVentas.map((s, i) => (
                                    <div key={i} title={`${s.fecha}: Gs. ${s.monto}`} style={{ 
                                        flex: 1, backgroundColor: '#3b82f6', 
                                        height: `${(s.monto / (Math.max(...statsVentas.map(x => x.monto)) || 1)) * 100}%`,
                                        borderRadius: '2px 2px 0 0'
                                    }}></div>
                                ))}
                            </div>
                        </div>
                        <div className="card">
                            <h3>Productos Estrella</h3>
                            <ul style={{ listStyle: 'none', padding: 0 }}>
                                {topProductos.map((p, i) => (
                                    <li key={i} style={{ display:'flex', justifyContent:'space-between', padding:'0.5rem 0', borderBottom:'1px solid #2a3441' }}>
                                        <span>{p.nombre}</span>
                                        <strong>{p.cantidad}</strong>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <section className="card wide" style={{marginTop:'2rem'}}>
                        <h3>Últimas Facturas</h3>
                        <table className="table">
                            <thead><tr><th>Nº</th><th>Cliente</th><th>Total</th><th>Estado</th><th>Acción</th></tr></thead>
                            <tbody>
                                {facturas.slice(0,5).map(f => (
                                    <tr key={f.id}>
                                        <td>{f.numero_documento}</td>
                                        <td>{f.receptor_nombre}</td>
                                        <td>{f.d_tot_gral_ope.toLocaleString()}</td>
                                        <td><span className={`badge ${f.estado_envio}`}>{f.estado_envio}</span></td>
                                        <td>
                                            <button className="linkish" onClick={()=>openKude(f.id)}>PDF</button>
                                            {" | "}
                                            <button className="linkish" onClick={()=>downloadXml(f.id)}>XML</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                </section>
            )}

            {activeTab === "presupuestos" && (
                <section>
                    <PresupuestosView empresaNombre={empresaNombre} onFacturar={handleFacturarPresupuesto} />
                </section>
            )}

            {activeTab === "factura" && (
                <section className="grid">
                    <FacturacionView emisor={emisor} productos={productos} refresh={refresh} initialFacturaParams={facturaInitParams} />
                </section>
            )}

            {activeTab === "inventario" && (
                <section>
                    <InventarioView productos={productos} refresh={refresh} />
                </section>
            )}

            {activeTab === "clientes" && (
                <section>
                    <ClientesView refresh={refresh} />
                </section>
            )}

            {activeTab === "compras" && (
                <section>
                    <ComprasView compras={compras} refresh={refresh} />
                </section>
            )}

            {activeTab === "lotes" && (
                <section>
                    <LotesView />
                </section>
            )}

            {activeTab === "usuarios" && isCompanyAdmin && (
                <section>
                    <UsuariosView usuariosEmpresa={usuariosEmpresa} usuarioEmail={usuarioEmail} refresh={refresh} />
                </section>
            )}

            {activeTab === "config" && (
                <section className="grid">
                    <div className="card">
                        <h2>Configuración SIFEN</h2>
                        <form className="form" onSubmit={e=>{e.preventDefault(); onUpdateEmisorConfig();}}>
                            <label className="full">Secreto CSC <input type="password" value={cscSec} onChange={e=>setCscSec(e.target.value)} /></label>
                            <label className="full">ID CSC <input value={cscId} onChange={e=>setCscId(e.target.value)} /></label>
                            <button type="submit" className="secondary full">Guardar Credenciales</button>
                        </form>
                        <div className="v-stack" style={{marginTop:'2rem'}}>
                             <button className="linkish" onClick={()=>loadEquipos().then(()=>setShowEquiposModal(true))}>Ver Equipos Autorizados</button>
                             <button className="linkish" onClick={()=>setShowCertGuide(true)}>¿Cómo obtener Certificado Digital?</button>
                        </div>
                    </div>
                </section>
            )}
        </main>
      )}

      {!authed && (
        <section className="grid" style={{marginTop:'4rem'}}>
            <div className="card">
                <h2>Acceso a Panel</h2>
                <form onSubmit={onLogin} className="form">
                    <label className="full">Email de Acceso <input value={loginEmail} onChange={e=>setLoginEmail(e.target.value)} /></label>
                    <label className="full">Contraseña <input type="password" value={loginPass} onChange={e=>setLoginPass(e.target.value)} /></label>
                    <button type="submit" className="primary full" disabled={loading}>Entrar</button>
                </form>
                <div id="google-login-btn" style={{marginTop:'1rem', display:'flex', justifyContent:'center'}}></div>
            </div>
            <div className="card">
                <h2>Solicitar Factura Electrónica</h2>
                <p className="hint">Solicita el alta de tu empresa para comenzar a emitir Documentos Electrónicos.</p>
                <form onSubmit={onRegister} className="form" style={{marginTop:'1rem'}}>
                    <div className="v-stack" style={{gap:'1rem', marginBottom:'1.5rem'}}>
                        <div id="reg-google-btn" style={{display:'flex', justifyContent:'center'}}></div>
                        {regGoogleToken && (
                            <div className="alert success small" style={{textAlign:'center'}}>
                                ✓ Google Vinculado: <strong>{regEmail}</strong>
                                <button type="button" className="linkish" style={{marginLeft:'10px', fontSize:'0.8rem'}} onClick={()=>setRegGoogleToken(null)}>Cambiar</button>
                            </div>
                        )}
                    </div>
                    
                    <label className="full">Nombre Comercial de Empresa <input value={regEmpresa} onChange={e=>setRegEmpresa(e.target.value)} placeholder="Ej: Mi Negocio S.A." /></label>
                    <label>RUC (con DV) <input value={regRuc} onChange={e=>setRegRuc(e.target.value)} placeholder="80000000-0" /></label>
                    <label>Razón Social <input value={regRazon} onChange={e=>setRegRazon(e.target.value)} placeholder="Nombre Legal" /></label>
                    
                    {!regGoogleToken && (
                        <>
                            <label className="full">Email Administrador <input value={regEmail} onChange={e=>setRegEmail(e.target.value)} /></label>
                            <label className="full">Contraseña <input type="password" value={regPass} onChange={e=>setRegPass(e.target.value)} /></label>
                        </>
                    )}
                    
                    <button type="submit" className="secondary full" disabled={loading}>Enviar Solicitud de Alta</button>
                </form>
            </div>
        </section>
      )}

      <footer className="footer">
        <p>© 2026 Denarius System - Paraguay · SIFEN Cloud Native</p>
      </footer>



      {showCertGuide && (
        <div className="modal-overlay" onClick={() => setShowCertGuide(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '600px', background:'var(--panel)', padding:'2rem', borderRadius:'12px'}}>
            <h2>Obtener Firma Digital .p12</h2>
            <p>1. Contacta a un PSC autorizado (Bancard, Documenta, etc).</p>
            <p>2. Solicita el formato .p12 (No token físico).</p>
            <p>3. Envía el archivo a soporte@denarius.com.py para su integración.</p>
            <button className="secondary full" style={{marginTop:'1rem'}} onClick={() => setShowCertGuide(false)}>Cerrar</button>
          </div>
        </div>
      )}

      {showEquiposModal && (
        <div className="modal-overlay" onClick={() => setShowEquiposModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '800px', background:'var(--panel)', padding:'2rem', borderRadius:'12px'}}>
            <h2>Equipos y Seguridad</h2>
            <table className="table">
              <thead><tr><th>ID Dispositivo</th><th>Estado</th><th>Acciones</th></tr></thead>
              <tbody>
                {equipos.map(eq => (
                  <tr key={eq.id}>
                    <td><small className="mono">{eq.device_id}</small></td>
                    <td>{eq.autorizado ? 'AUTORIZADO' : 'BLOQUEADO'}</td>
                    <td>
                        <button className="linkish" onClick={() => onToggleEquipo(eq.id, eq.autorizado)}>{eq.autorizado ? 'Bloquear' : 'Autorizar'}</button>
                        {" | "}
                        <button className="linkish danger" onClick={() => onDeleteEquipo(eq.id)}>Borrar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button className="secondary full" style={{marginTop:'1rem'}} onClick={() => setShowEquiposModal(false)}>Cerrar</button>
          </div>
        </div>
      )}

      {editEmpresa && (
        <div className="modal-overlay" onClick={() => setEditEmpresa(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '500px', background: 'var(--panel)', padding: '2rem', borderRadius: '12px', position: 'relative'}}>
            <button type="button" onClick={() => setEditEmpresa(null)} style={{position: 'absolute', top: '1rem', right: '1rem', background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text)'}}>✕</button>
            <h2>Editar Empresa #{editEmpresa.id}</h2>
            <form onSubmit={onSaveEdit} className="form" style={{marginTop: '1rem'}}>
              <label className="full">Nombre <input value={editFields.nombre} onChange={e => setEditFields({...editFields, nombre: e.target.value})} /></label>
              <label className="full">Razón Social <input value={editFields.razon_social} onChange={e => setEditFields({...editFields, razon_social: e.target.value})} /></label>
              <label className="full">RUC <input value={editFields.ruc_con_dv} onChange={e => setEditFields({...editFields, ruc_con_dv: e.target.value})} /></label>
              <button type="submit" className="primary full" disabled={loading} style={{marginTop: '1rem'}}>Guardar Cambios</button>
            </form>

            <hr style={{margin: '1.5rem 0', borderColor: 'var(--border)'}} />
            <h3>Accesos de Administrador</h3>
            <div className="form">
              <label className="full">Email Admin
                <div style={{display: 'flex', gap: '0.5rem', marginTop: '0.5rem'}}>
                  <input style={{flex: 1}} value={editFields.email_admin} onChange={e => setEditFields({...editFields, email_admin: e.target.value})} />
                  <button type="button" className="secondary" disabled={loading} onClick={onSaveEmailAdmin}>Actualizar Email</button>
                </div>
              </label>
              <button type="button" className="highlight full" disabled={loading} onClick={handleResetPassword} style={{marginTop: '0.5rem'}}>
                Reenviar contraseña al correo
              </button>
            </div>
          </div>
        </div>
      )}

      {previewImg && (
        <div className="modal-overlay" onClick={() => setPreviewImg(null)}>
          <img src={previewImg} style={{maxWidth:'90vw', maxHeight:'80vh'}} />
        </div>
      )}
    </div>
  );
}
