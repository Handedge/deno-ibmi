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
import { api, token, onSessionExpired } from "./api.js";
import SignIn from "./SignIn.jsx";
import System from "./System.jsx";
import Clients from "./Clients.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [checked, setChecked] = useState(false);
  const [signInMessage, setSignInMessage] = useState("");
  const [toasts, setToasts] = useState([]);

  const notify = useCallback((kind, title, subtitle = "") => {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, kind, title, subtitle }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);

  // is the session still valid after a page reload?
  useEffect(() => {
    onSessionExpired(() => {
      setUser(null);
      setSignInMessage("Your session has expired, please sign in again.");
    });
    if (!token.get()) return setChecked(true);
    api.session()
      .then((s) => setUser(s.utilisateur))
      .catch(() => token.clear())
      .finally(() => setChecked(true));
  }, []);

  const signOut = async () => {
    try { await api.signOut(); } catch { /* session already closed */ }
    token.clear();
    setUser(null);
    setSignInMessage("");
  };

  if (!checked) return null;

  if (!user) {
    return (
      <Theme theme="g100">
        <SignIn
          message={signInMessage}
          onSignedIn={(u) => { setSignInMessage(""); setUser(u); }}
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
            <HeaderGlobalAction aria-label={`Signed in: ${user}`} tooltipAlignment="end">
              <UserAvatar size={20} />
            </HeaderGlobalAction>
            <HeaderGlobalAction aria-label="Sign out" tooltipAlignment="end" onClick={signOut}>
              <Logout size={20} />
            </HeaderGlobalAction>
          </HeaderGlobalBar>
        </Header>
      </Theme>
      <Theme theme="g10">
        <Content className="page">
          <System user={user} />
          <Clients notify={notify} />
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
