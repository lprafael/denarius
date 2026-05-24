import React, { useState } from "react";
import { createUsuario, updateUsuario, deleteUsuario } from "../api";

interface UsuariosViewProps {
  usuariosEmpresa: any[];
  usuarioEmail: string;
  refresh: () => Promise<void>;
}

export function UsuariosView({ usuariosEmpresa, usuarioEmail, refresh }: UsuariosViewProps) {
  const [showUsuarioModal, setShowUsuarioModal] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function onSaveUsuario(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      if (editingUsuario?.id) {
        await updateUsuario(editingUsuario.id, editingUsuario);
      } else {
        await createUsuario(editingUsuario);
      }
      setShowUsuarioModal(false);
      setEditingUsuario(null);
      await refresh();
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  async function onToggleUsuario(id: number, currentActivo: boolean) {
    if (!window.confirm(`¿${currentActivo ? "Deshabilitar" : "Habilitar"} usuario?`)) return;
    try {
      if (currentActivo) await deleteUsuario(id);
      else await updateUsuario(id, { activo: true });
      await refresh();
    } catch (ex) {
      setErr(String(ex));
    }
  }

  return (
    <div className="card wide">
      {err && <div className="alert">{err}</div>}
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
              <button type="submit" className="primary full" style={{marginTop:'1rem'}} disabled={loading}>Guardar Usuario</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
