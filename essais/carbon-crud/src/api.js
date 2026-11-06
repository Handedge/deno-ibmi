// Access to the Deno API on IBMI (proxied by Vite on /api). The session token lives in
// sessionStorage: it disappears when the tab is closed.

export class ErreurApi extends Error {
  constructor(message, statut, detail) {
    super(message);
    this.statut = statut;
    this.detail = detail;
  }
}

const CLE = "ibmi-jeton";
export const jeton = {
  lire: () => sessionStorage.getItem(CLE),
  ecrire: (j) => sessionStorage.setItem(CLE, j),
  effacer: () => sessionStorage.removeItem(CLE),
};

let surExpiration = () => {};
export const quandSessionExpire = (f) => { surExpiration = f; };

async function appel(methode, chemin, corps) {
  const entetes = { "content-type": "application/json" };
  const j = jeton.lire();
  if (j) entetes.authorization = `Bearer ${j}`;
  const r = await fetch(chemin, {
    method: methode,
    headers: entetes,
    body: corps === undefined ? undefined : JSON.stringify(corps),
  });
  if (r.status === 204) return null;
  const donnees = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && chemin !== "/api/session") {
      jeton.effacer();
      surExpiration();
    }
    throw new ErreurApi(donnees.erreur ?? `erreur HTTP ${r.status}`, r.status, donnees);
  }
  return donnees;
}

export const api = {
  connecter: (utilisateur, motDePasse) => appel("POST", "/api/session", { utilisateur, motDePasse }),
  deconnecter: () => appel("DELETE", "/api/session"),
  session: () => appel("GET", "/api/session"),
  systeme: () => appel("GET", "/api/systeme"),
  clients: (q = "") => appel("GET", `/api/clients?q=${encodeURIComponent(q)}`),
  creer: (fiche) => appel("POST", "/api/clients", fiche),
  modifier: (id, fiche) => appel("PUT", `/api/clients/${id}`, fiche),
  supprimer: (id) => appel("DELETE", `/api/clients/${id}`),
};
