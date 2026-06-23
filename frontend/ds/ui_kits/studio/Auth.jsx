/* global React, Icon */
function Auth({ onLogin }) {
  const [tab, setTab] = React.useState('login');
  const [form, setForm] = React.useState({ name: 'Elena Vázquez', email: 'elena@lab.science', pass: '••••••••' });
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));
  const feats = [
    { icon: 'GitBranch', text: 'Flow Designer visual con LangGraph' },
    { icon: 'Bot', text: 'Agentes: Investigador, Redactor, Revisor…' },
    { icon: 'Zap', text: 'Ejecución en tiempo real' },
    { icon: 'Shield', text: 'RAG privado · revisión human-in-the-loop' },
  ];
  return (
    <div className="auth">
      <div className="auth-left">
        <div className="inner">
          <div className="auth-brand">
            <img src="../../assets/logomark.svg" width="40" height="40" alt="" />
            <div><div className="name">AlejandrIA</div><div className="sub">MAGAZINE</div></div>
          </div>
          <h1 className="auth-head">Redacta ciencia con rigor, publícala con confianza.</h1>
          <p className="auth-tag">La plataforma agéntica para crear, revisar y publicar artículos científicos asistidos por IA.</p>
          <div className="auth-feats">
            {feats.map((f, i) => (
              <div className="auth-feat" key={i}>
                <span className="ic"><Icon name={f.icon} size={15} /></span>{f.text}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="auth-right">
        <form className="auth-form" onSubmit={(e) => { e.preventDefault(); onLogin({ name: form.name, role: 'Autora' }); }}>
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: 'var(--ink-100)' }}>{tab === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}</h2>
            <p style={{ fontSize: 13.5, color: 'var(--text-muted)', marginTop: 4 }}>{tab === 'login' ? 'Accede a tu espacio de trabajo' : 'Únete a AlejandrIA Magazine'}</p>
          </div>
          <div className="tabs" style={{ alignSelf: 'flex-start' }}>
            <button type="button" className={`tab${tab === 'login' ? ' active' : ''}`} onClick={() => setTab('login')}>Iniciar sesión</button>
            <button type="button" className={`tab${tab === 'register' ? ' active' : ''}`} onClick={() => setTab('register')}>Registrarse</button>
          </div>
          {tab === 'register' && (
            <div className="field"><label>Nombre completo</label><input className="inp" value={form.name} onChange={set('name')} /></div>
          )}
          <div className="field"><label>Email</label><input className="inp" type="email" value={form.email} onChange={set('email')} /></div>
          <div className="field"><label>Contraseña</label><input className="inp" type="password" value={form.pass} onChange={set('pass')} /></div>
          <button className="btn btn-primary btn-lg btn-block" type="submit">{tab === 'login' ? 'Entrar' : 'Crear cuenta'}</button>
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', textAlign: 'center' }}>
            {tab === 'login' ? '¿No tienes cuenta? ' : '¿Ya tienes cuenta? '}
            <button type="button" onClick={() => setTab(tab === 'login' ? 'register' : 'login')}
              style={{ background: 'none', border: 'none', color: 'var(--brand)', fontWeight: 600, fontSize: 'inherit', cursor: 'pointer' }}>
              {tab === 'login' ? 'Regístrate' : 'Inicia sesión'}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
window.Auth = Auth;
