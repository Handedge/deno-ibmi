import { useState } from "react";
import { Button, Form, InlineNotification, PasswordInput, Stack, TextInput, Tile } from "@carbon/react";
import { ArrowRight } from "@carbon/icons-react";
import { api, token } from "./api.js";

export default function SignIn({ onSignedIn, message }) {
  const [profile, setProfile] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const r = await api.signIn(profile, password);
      token.set(r.jeton);
      setPassword("");
      onSignedIn(r.utilisateur);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="sign-in">
      <Tile>
        <h1 className="cds--type-productive-heading-05">IBMI</h1>
        <p className="subtitle">Sign in with your IBM i profile</p>
        <Form onSubmit={submit}>
          <Stack gap={6}>
            {message && <InlineNotification kind="info" title={message} hideCloseButton lowContrast />}
            {error && (
              <InlineNotification kind="error" title="Sign-in refused" subtitle={error} hideCloseButton lowContrast />
            )}
            <TextInput
              id="profile"
              labelText="User profile"
              autoComplete="username"
              maxLength={10}
              value={profile}
              onChange={(e) => setProfile(e.target.value.toUpperCase())}
              helperText="Your IBM i profile"
            />
            <PasswordInput
              id="password"
              labelText="Password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              showPasswordLabel="Show password"
              hidePasswordLabel="Hide password"
            />
            <p className="cds--label">
              Warning: every failure counts towards the IBM i sign-on attempt limit (QMAXSIGN).
            </p>
            <Button type="submit" renderIcon={ArrowRight} disabled={!profile || !password || busy}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </Stack>
        </Form>
      </Tile>
    </div>
  );
}
