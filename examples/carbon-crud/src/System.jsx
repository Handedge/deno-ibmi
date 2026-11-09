import { useEffect, useState } from "react";
import { Column, Grid, ProgressBar, SkeletonText, Tile } from "@carbon/react";
import { api } from "./api.js";

const formatDuration = (s) => {
  if (s == null) return "–";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d} d ${h} h` : h ? `${h} h ${m} min` : `${m} min`;
};

function Metric({ label, value, footer }) {
  return (
    <Column sm={4} md={4} lg={4}>
      <Tile>
        <div className="label">{label}</div>
        {value === undefined ? <SkeletonText /> : <div className="value">{value}</div>}
        {footer}
      </Tile>
    </Column>
  );
}

/** System indicators, refreshed every 15 seconds. */
export default function System({ user }) {
  const [s, setS] = useState(null);

  useEffect(() => {
    let active = true;
    const load = () => api.system().then((r) => active && setS(r)).catch(() => {});
    load();
    const t = setInterval(load, 15000);
    return () => { active = false; clearInterval(t); };
  }, []);

  return (
    <Grid className="metrics" narrow fullWidth>
      <Column sm={4} md={8} lg={16}>
        <h2 className="page-title cds--type-productive-heading-04">
          Hello {user}
        </h2>
      </Column>
      <Metric
        label="Partition"
        value={s && `${s.hote}`}
        footer={s && <div className="label">IPL {formatDuration(s.uptimeSysteme)} ago</div>}
      />
      <Metric
        label="System ASP used"
        value={s && `${Number(s.SYSTEM_ASP_USED).toLocaleString("en-US")} %`}
        footer={s && (
          <ProgressBar
            label=""
            hideLabel
            value={Number(s.SYSTEM_ASP_USED)}
            status={s.SYSTEM_ASP_USED >= 80 ? "error" : "active"}
            size="small"
          />
        )}
      />
      <Metric
        label="Active / total jobs"
        value={s && `${s.ACTIVE_JOBS_IN_SYSTEM.toLocaleString("en-US")} / ${s.TOTAL_JOBS_IN_SYSTEM.toLocaleString("en-US")}`}
      />
      <Metric
        label="API Deno"
        value={s && `Deno ${s.deno}`}
        footer={s && (
          <div className="label">
            V8 {s.v8} · {s.sessions} session(s) · up for {formatDuration(s.uptimeApi)}
          </div>
        )}
      />
    </Grid>
  );
}
