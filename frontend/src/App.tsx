import { useCallback, useEffect, useRef, useState } from "react";
declare global { interface Window { google: any } }

import logo from "./assets/logo.png";
import {
  createFactura,
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
  consultarRuc,
  getClienteByRuc,
  upsertCliente,

  getDepartamentos,
  getDistritos,
  getBarrios,
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
  createProducto,
  updateProducto,
  deleteProducto,
  listCompras,
  syncCompras,
  getProyeccionIva,
  getStatsVentas,
  getTopProductos,
  listUsuarios,
  createUsuario,
  deleteUsuario,
  updateUsuario,
  type EmisorOut,

  type FacturaCreate,
  type FacturaOut,
} from "./api";


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
    max_equipos: 0
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

  const [ruc, setRuc] = useState("");
  const [dv, setDv] = useState("");
  const [nombre, setNombre] = useState("");
  const [clienteEmail, setClienteEmail] = useState("");
  const [clienteTel, setClienteTel] = useState("");
  const [clienteDir, setClienteDir] = useState("");
  const [deptoId, setDeptoId] = useState<number>(0);
  const [distritoId, setDistritoId] = useState<number>(0);
  const [barrioId, setBarrioId] = useState<number>(0);

  const googleInitialized = useRef(false);

  const [showClienteModal, setShowClienteModal] = useState<boolean>(false);
  const [deptos, setDeptos] = useState<any[]>([]);
  const [distritos_local, setDistritosLocal] = useState<any[]>([]);
  const [barrios_local, setBarriosLocal] = useState<any[]>([]);
  const [lineas, setLineas] = useState<any[]>([
    { producto_id: undefined, d_cod_int: "ART001", d_des_pro_ser: "Producto o servicio", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10 },
  ]);

  const [activeTab, setActiveTab] = useState<"dashboard" | "factura" | "inventario" | "compras" | "usuarios" | "config">("dashboard");
  const [productos, setProductos] = useState<any[]>([]);
  const [compras, setCompras] = useState<any[]>([]);
  const [usuariosEmpresa, setUsuariosEmpresa] = useState<any[]>([]);
  const [proyeccionIva, setProyeccionIva] = useState<any | null>(null);
  const [statsVentas, setStatsVentas] = useState<any[]>([]);
  const [topProductos, setTopProductos] = useState<any[]>([]);
  const [showProductoModal, setShowProductoModal] = useState(false);
  const [editingProducto, setEditingProducto] = useState<any>(null);
  const [showUsuarioModal, setShowUsuarioModal] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState<any>(null);

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
           const l = await listFacturas(adminFacturaEmpresaId);
           setFacturas(l);
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

        const d = await getDepartamentos();
        setDeptos(d);
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
    async function fetchDistritos() {
      if (deptoId >= 0) {
        const d = await getDistritos(deptoId);
        setDistritosLocal(d);
      }
    }
    if (authed) fetchDistritos();
  }, [deptoId, authed]);

  useEffect(() => {
    async function fetchBarrios() {
      if (deptoId >= 0 && distritoId >= 0) {
        const b = await getBarrios(deptoId, distritoId);
        setBarriosLocal(b);
      }
    }
    if (authed) fetchBarrios();
  }, [deptoId, distritoId, authed]);

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

  const [clienteEncontrado, setClienteEncontrado] = useState<any>(null);

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
        const r = await consultarRuc(val);
        if (r.ok && r.razon_social) {
          setNombre(r.razon_social);
          if (r.dv) setDv(r.dv);
          // It's from SIFEN but NOT in local DB
          setClienteEncontrado({ _is_new_sifen: true });
        }
      } catch (err) {}
    }
  }

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
          d_des_ciu: distritos_local.find(d => d.id === distritoId)?.nombre || "",
          c_bar: barrioId,
          d_des_bar: barrios_local.find(b => b.id === barrioId)?.nombre || ""
        });
      } catch (e) {}
      setRuc(""); setNombre(""); setLineas([{ producto_id: undefined, d_cod_int: "", d_des_pro_ser: "", d_cant_pro_ser: 1, d_p_uni_pro_ser: 0, d_tasa_iva: 10 }]);
      await refresh();
      alert("Factura emitida");
    } catch (ex) {
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
      restriccion_equipos: !!emp.restriccion_equipos, max_equipos: emp.max_equipos || 0
    });
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

  async function onSaveProducto(e: React.FormEvent) {
    e.preventDefault(); if (!editingProducto) return;
    setLoading(true);
    try {
      if (editingProducto.id) await updateProducto(editingProducto.id, editingProducto);
      else await createProducto(editingProducto);
      setShowProductoModal(false); setEditingProducto(null);
      await refresh();
    } catch (ex) { setErr(String(ex)); } finally { setLoading(false); }
  }

  async function onDeleteProducto(id: number) {
    if (!window.confirm("¿Eliminar?")) return;
    try { await deleteProducto(id); await refresh(); } catch (ex) { setErr(String(ex)); }
  }

  async function onSyncCompras() {
    setLoading(true);
    try { await syncCompras(); await refresh(); alert("Sincronizado"); }
    catch (ex) { setErr(String(ex)); } finally { setLoading(false); }
  }

  async function onUpdateEmisorConfig() {
    setLoading(true);
    try {
      const updated = await updateEmisor({ id_csc: cscId, csc_secreto: cscSec });
      setEmisor(updated); alert("Actualizado");
    } catch (e) { setErr(String(e)); } finally { setLoading(false); }
  }

  async function onSaveUsuario(e: React.FormEvent) {
    e.preventDefault(); setLoading(true);
    try {
      if (editingUsuario?.id) {
          await updateUsuario(editingUsuario.id, editingUsuario);
      } else {
          await createUsuario(editingUsuario);
      }
      setShowUsuarioModal(false); setEditingUsuario(null);
      await refresh();
    } catch (ex) { setErr(String(ex)); } finally { setLoading(false); }
  }

  async function onToggleUsuario(id: number, currentActivo: boolean) {
    if (!window.confirm(`¿${currentActivo ? "Deshabilitar" : "Habilitar"} usuario?`)) return;
    try {
      if (currentActivo) await deleteUsuario(id);
      else await updateUsuario(id, { activo: true });
      await refresh();
    } catch (ex) { setErr(String(ex)); }
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
          <button className={activeTab === "inventario" ? "active" : ""} onClick={() => setActiveTab("inventario")}>Stock</button>
          <button className={activeTab === "compras" ? "active" : ""} onClick={() => setActiveTab("compras")}>Compras (IVA)</button>
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
                                        <button className="linkish" onClick={() => { const full = empresas.find(e=>e.id===d.empresa_id); if(full) onEditClick(full); }}>✏️</button>
                                        {" | "}
                                        <button className="linkish" onClick={() => onToggleEmpresa(d.empresa_id)}>
                                            {d.estado === 'activo' ? '🚫' : '✅'}
                                        </button>
                                        {" | "}
                                        <button className="linkish" onClick={async () => {
                                            setAdminFacturaEmpresaId(d.empresa_id);
                                            setAdminEmpresaNombre(d.nombre);
                                            setAdminActiveTab("facturas");
                                            const l = await listFacturas(d.empresa_id);
                                            setFacturas(l);
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
                        <button className="linkish" onClick={() => { setAdminFacturaEmpresaId(undefined); setAdminEmpresaNombre("Global"); refresh(); }}>Limpiar Filtro</button>
                    </div>
                    <table className="table">
                        <thead><tr><th>ID</th><th>Fecha</th><th>Empresa</th><th>Monto</th><th>Estado</th></tr></thead>
                        <tbody>
                            {facturas.map(f => (
                                <tr key={f.id}>
                                    <td>{f.id}</td>
                                    <td>{new Date(f.created_at).toLocaleDateString()}</td>
                                    <td>{f.empresa_id}</td>
                                    <td>{f.d_tot_gral_ope.toLocaleString()}</td>
                                    <td>{f.estado_envio}</td>
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

            {activeTab === "factura" && (
                <section className="grid">
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
                </section>
            )}

            {activeTab === "inventario" && (
                <section className="card wide">
                    <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
                        <h2>Gestión de Stock</h2>
                        <button className="primary" onClick={() => { setEditingProducto({ sku: "", descripcion: "", precio_venta: 0, precio_costo: 0, stock_actual: 0 }); setShowProductoModal(true); }}>+ Nuevo Producto</button>
                    </div>
                    <table className="table">
                        <thead><tr><th>SKU</th><th>Descripción</th><th>Stock</th><th>Precio</th><th>Acciones</th></tr></thead>
                        <tbody>
                            {productos.map(p => (
                                <tr key={p.id}>
                                    <td className="mono">{p.sku}</td>
                                    <td>{p.descripcion}</td>
                                    <td className={p.stock_actual < 5 ? 'error-text' : 'success-text'}>{p.stock_actual}</td>
                                    <td>{p.precio_venta.toLocaleString()}</td>
                                    <td>
                                        <button className="linkish" onClick={() => { setEditingProducto(p); setShowProductoModal(true); }}>✏️</button>
                                        {" | "}
                                        <button className="linkish danger" onClick={() => onDeleteProducto(p.id)}>🗑️</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </section>
            )}

            {activeTab === "compras" && (
                <section className="card wide">
                    <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
                        <h2>Facturas Recibidas</h2>
                        <button className="secondary" onClick={onSyncCompras} disabled={loading}>Sincronizar SIFEN</button>
                    </div>
                    <table className="table">
                        <thead><tr><th>Fecha</th><th>Emisor</th><th>RUC Emisor</th><th>Total</th><th>IVA</th></tr></thead>
                        <tbody>
                            {compras.map(c => (
                                <tr key={c.id}>
                                    <td>{new Date(c.fecha_emision).toLocaleDateString()}</td>
                                    <td>{c.emisor_razon_social}</td>
                                    <td>{c.emisor_ruc}</td>
                                    <td>{c.monto_total.toLocaleString()}</td>
                                    <td>{c.monto_iva.toLocaleString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </section>
            )}

            {activeTab === "usuarios" && isCompanyAdmin && (
                <section className="card wide">
                    <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
                        <h2>Operadores de la Empresa</h2>
                        <button className="primary" onClick={() => { setEditingUsuario({ nombre: "", email: "", password: "", rol: "operador" }); setShowUsuarioModal(true); }}>+ Nuevo Operador</button>
                    </div>
                    <table className="table">
                        <thead><tr><th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
                        <tbody>
                            {usuariosEmpresa.map(u => (
                                <tr key={u.id}>
                                    <td>{u.nombre}</td>
                                    <td>{u.email}</td>
                                    <td><span className="badge info">{u.rol.toUpperCase()}</span></td>
                                    <td><span className={`badge ${u.activo ? 'activo' : 'inactivo'}`}>{u.activo ? 'ACTIVO' : 'INACTIVO'}</span></td>
                                    <td>
                                        <button className="linkish" onClick={() => { setEditingUsuario(u); setShowUsuarioModal(true); }}>✏️</button>
                                        {" | "}
                                        {u.email !== usuarioEmail && (
                                            <button className="linkish" onClick={() => onToggleUsuario(u.id, u.activo)}>
                                                {u.activo ? '🚫' : '✅'}
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
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

      {showProductoModal && editingProducto && (
          <div className="modal-overlay" onClick={()=>setShowProductoModal(false)}>
              <div className="modal-content" onClick={e=>e.stopPropagation()} style={{background:'var(--panel)', padding:'2rem', borderRadius:'12px', width:'400px'}}>
                  <h2>{editingProducto.id ? "Editar" : "Nuevo"} Producto</h2>
                  <form onSubmit={onSaveProducto} className="form">
                      <label className="full">SKU <input value={editingProducto.sku} onChange={e=>setEditingProducto({...editingProducto, sku:e.target.value})} /></label>
                      <label className="full">Descripción <input value={editingProducto.descripcion} onChange={e=>setEditingProducto({...editingProducto, descripcion:e.target.value})} /></label>
                      <label>Venta Gs. <input type="number" value={editingProducto.precio_venta} onChange={e=>setEditingProducto({...editingProducto, precio_venta:Number(e.target.value)})} /></label>
                      <label>Stock <input type="number" value={editingProducto.stock_actual} onChange={e=>setEditingProducto({...editingProducto, stock_actual:Number(e.target.value)})} /></label>
                      <button type="submit" className="primary full" style={{marginTop:'1rem'}}>Guardar Cambios</button>
                  </form>
              </div>
          </div>
      )}

      {showUsuarioModal && editingUsuario && (
          <div className="modal-overlay" onClick={()=>setShowUsuarioModal(false)}>
              <div className="modal-content" onClick={e=>e.stopPropagation()} style={{background:'var(--panel)', padding:'2rem', borderRadius:'12px', width:'400px'}}>
                  <h2>{editingUsuario.id ? "Editar" : "Nuevo"} Operador</h2>
                  <form onSubmit={onSaveUsuario} className="form">
                      <label className="full">Nombre Completo <input value={editingUsuario.nombre} onChange={e=>setEditingUsuario({...editingUsuario, nombre:e.target.value})} /></label>
                      <label className="full">Email <input value={editingUsuario.email} onChange={e=>setEditingUsuario({...editingUsuario, email:e.target.value})} /></label>
                      <label className="full">Contraseña {editingUsuario.id && <small>(Dejar vacío para mantener)</small>} <input type="password" value={editingUsuario.password || ""} onChange={e=>setEditingUsuario({...editingUsuario, password:e.target.value})} /></label>
                      <label className="full">Rol <select value={editingUsuario.rol} onChange={e=>setEditingUsuario({...editingUsuario, rol:e.target.value})}>
                          <option value="operador">Operador (Solo emisión)</option>
                          <option value="admin">Administrador (Gestión total)</option>
                      </select></label>
                      <button type="submit" className="primary full" style={{marginTop:'1rem'}}>Guardar Usuario</button>
                  </form>
              </div>
          </div>
      )}

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
                        d_des_ciu: distritos_local.find(d => d.id === distritoId)?.nombre || "",
                        c_bar: barrioId,
                        d_des_bar: barrios_local.find(b => b.id === barrioId)?.nombre || ""
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
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '500px', background: 'var(--panel)', padding: '2rem', borderRadius: '12px'}}>
            <h2>Editar Empresa #{editEmpresa.id}</h2>
            <form onSubmit={onSaveEdit} className="form" style={{marginTop: '1rem'}}>
              <label className="full">Nombre <input value={editFields.nombre} onChange={e => setEditFields({...editFields, nombre: e.target.value})} /></label>
              <label className="full">Razón Social <input value={editFields.razon_social} onChange={e => setEditFields({...editFields, razon_social: e.target.value})} /></label>
              <label className="full">RUC <input value={editFields.ruc_con_dv} onChange={e => setEditFields({...editFields, ruc_con_dv: e.target.value})} /></label>
              <button type="submit" className="primary full" disabled={loading} style={{marginTop: '1rem'}}>Guardar Cambios</button>
            </form>
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
