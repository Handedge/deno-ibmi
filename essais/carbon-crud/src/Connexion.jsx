import { useState } from "react";
import { Button, Form, InlineNotification, PasswordInput, Stack, TextInput, Tile } from "@carbon/react";
import { ArrowRight } from "@carbon/icons-react";
import { api, jeton } from "./api.js";

export default function Connexion({ onConnecte, message }) {
  const [profil, setProfil] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [enCours, setEnCours] = useState(false);

  const soumettre = async (e) => {
    e.preventDefault();
    setErreur("");
    setEnCours(true);
    try {
      const r = await api.connecter(profil, motDePasse);
      jeton.ecrire(r.jeton);
      setMotDePasse("");
      onConnecte(r.utilisateur);
    } catch (err) {
      setErreur(err.message);
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="connexion">
      <Tile>
        <h1 className="cds--type-productive-heading-05">IBMI</h1>
        <p className="sous-titre">Connexion avec votre profil IBM i</p>
        <Form onSubmit={soumettre}>
          <Stack gap={6}>
            {message && <InlineNotification kind="info" title={message} hideCloseButton lowContrast />}
            {erreur && (
              <InlineNotification kind="error" title="Connexion refusée" subtitle={erreur} hideCloseButton lowContrast />
            )}
            <TextInput
              id="profil"
              labelText="Profil utilisateur"
              autoComplete="username"
              maxLength={10}
              value={profil}
              onChange={(e) => setProfil(e.target.value.toUpperCase())}
              helperText="Votre profil IBM i"
            />
            <PasswordInput
              id="mot-de-passe"
              labelText="Mot de passe"
              autoComplete="current-password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              showPasswordLabel="Afficher le mot de passe"
              hidePasswordLabel="Masquer le mot de passe"
            />
            <p className="cds--label">
              Attention : chaque échec compte dans la limite de tentatives d'IBM i (QMAXSIGN).
            </p>
            <Button type="submit" renderIcon={ArrowRight} disabled={!profil || !motDePasse || enCours}>
              {enCours ? "Connexion…" : "Se connecter"}
            </Button>
          </Stack>
        </Form>
      </Tile>
    </div>
  );
}
