import { useEffect, useState } from "react";
import { Column, Grid, ProgressBar, SkeletonText, Tile } from "@carbon/react";
import { api } from "./api.js";

const duree = (s) => {
  if (s == null) return "–";
  const j = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return j ? `${j} j ${h} h` : h ? `${h} h ${m} min` : `${m} min`;
};

function Indicateur({ libelle, valeur, enfant }) {
  return (
    <Column sm={4} md={4} lg={4}>
      <Tile>
        <div className="libelle">{libelle}</div>
        {valeur === undefined ? <SkeletonText /> : <div className="valeur">{valeur}</div>}
        {enfant}
      </Tile>
    </Column>
  );
}

/** System indicators, refreshed every 15 seconds. */
export default function Systeme({ utilisateur }) {
  const [s, setS] = useState(null);

  useEffect(() => {
    let actif = true;
    const charger = () => api.systeme().then((r) => actif && setS(r)).catch(() => {});
    charger();
    const t = setInterval(charger, 15000);
    return () => { actif = false; clearInterval(t); };
  }, []);

  return (
    <Grid className="indicateurs" narrow fullWidth>
      <Column sm={4} md={8} lg={16}>
        <h2 className="titre-page cds--type-productive-heading-04">
          Bonjour {utilisateur}
        </h2>
      </Column>
      <Indicateur
        libelle="Partition"
        valeur={s && `${s.hote}`}
        enfant={s && <div className="libelle">IPL il y a {duree(s.uptimeSysteme)}</div>}
      />
      <Indicateur
        libelle="ASP système utilisé"
        valeur={s && `${Number(s.SYSTEM_ASP_USED).toLocaleString("fr-FR")} %`}
        enfant={s && (
          <ProgressBar
            label=""
            hideLabel
            value={Number(s.SYSTEM_ASP_USED)}
            status={s.SYSTEM_ASP_USED >= 80 ? "error" : "active"}
            size="small"
          />
        )}
      />
      <Indicateur
        libelle="Travaux actifs / total"
        valeur={s && `${s.ACTIVE_JOBS_IN_SYSTEM.toLocaleString("fr-FR")} / ${s.TOTAL_JOBS_IN_SYSTEM.toLocaleString("fr-FR")}`}
      />
      <Indicateur
        libelle="API Deno"
        valeur={s && `Deno ${s.deno}`}
        enfant={s && (
          <div className="libelle">
            V8 {s.v8} · {s.sessions} session(s) · active depuis {duree(s.uptimeApi)}
          </div>
        )}
      />
    </Grid>
  );
}
