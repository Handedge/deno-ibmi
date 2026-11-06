import { useCallback, useEffect, useState } from "react";
import {
  Content,
  Header,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderName,
  Theme,
  ToastNotification,
} from "@carbon/react";
import { Logout, UserAvatar } from "@carbon/icons-react";
import { api, jeton, quandSessionExpire } from "./api.js";
import Connexion from "./Connexion.jsx";
import Systeme from "./Systeme.jsx";
import Clients from "./Clients.jsx";

export default function App() {
  const [utilisateur, setUtilisateur] = useState(null);
  const [verifie, setVerifie] = useState(false);
  const [messageConnexion, setMessageConnexion] = useState("");
  const [toasts, setToasts] = useState([]);

  const notifier = useCallback((kind, title, subtitle = "") => {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, kind, title, subtitle }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);

  // is the session still valid after a page reload?
  useEffect(() => {
    quandSessionExpire(() => {
      setUtilisateur(null);
      setMessageConnexion("Votre session a expiré, reconnectez-vous.");
    });
    if (!jeton.lire()) return setVerifie(true);
    api.session()
      .then((s) => setUtilisateur(s.utilisateur))
      .catch(() => jeton.effacer())
      .finally(() => setVerifie(true));
  }, []);

  const deconnecter = async () => {
    try { await api.deconnecter(); } catch { /* session already closed */ }
    jeton.effacer();
    setUtilisateur(null);
    setMessageConnexion("");
  };

  if (!verifie) return null;

  if (!utilisateur) {
    return (
      <Theme theme="g100">
        <Connexion
          message={messageConnexion}
          onConnecte={(u) => { setMessageConnexion(""); setUtilisateur(u); }}
        />
      </Theme>
    );
  }

  return (
    <>
      <Theme theme="g100">
        <Header aria-label="IBMI">
          <HeaderName href="#" prefix="IBM i">IBMI · Deno</HeaderName>
          <HeaderGlobalBar>
            <HeaderGlobalAction aria-label={`Connecté : ${utilisateur}`} tooltipAlignment="end">
              <UserAvatar size={20} />
            </HeaderGlobalAction>
            <HeaderGlobalAction aria-label="Se déconnecter" tooltipAlignment="end" onClick={deconnecter}>
              <Logout size={20} />
            </HeaderGlobalAction>
          </HeaderGlobalBar>
        </Header>
      </Theme>
      <Theme theme="g10">
        <Content className="page">
          <Systeme utilisateur={utilisateur} />
          <Clients notifier={notifier} />
        </Content>
      </Theme>
      <div className="notifications">
        {toasts.map((t) => (
          <ToastNotification
            key={t.id}
            kind={t.kind}
            title={t.title}
            subtitle={t.subtitle}
            lowContrast
            onClose={() => setToasts((x) => x.filter((y) => y.id !== t.id))}
          />
        ))}
      </div>
    </>
  );
}
