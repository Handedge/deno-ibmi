import { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  DataTable,
  DataTableSkeleton,
  InlineNotification,
  Modal,
  OverflowMenu,
  OverflowMenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  TableToolbar,
  TableToolbarContent,
  TableToolbarSearch,
  TextInput,
} from "@carbon/react";
import { Add, Renew } from "@carbon/icons-react";
import { api } from "./api.js";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const ENTETES = [
  { key: "NOM", header: "Nom" },
  { key: "VILLE", header: "Ville" },
  { key: "EMAIL", header: "E-mail" },
  { key: "SOLDE", header: "Solde" },
  { key: "MAJ_PAR", header: "Modifié par" },
  { key: "MAJ_LE", header: "Modifié le" },
  { key: "actions", header: "" },
];
const VIDE = { nom: "", ville: "", email: "", solde: "0" };

/** Dialog for creating or editing a customer. */
function Fiche({ ouvert, client, onFermer, onEnregistre, notifier }) {
  const [f, setF] = useState(VIDE);
  const [erreur, setErreur] = useState("");
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    if (!ouvert) return;
    setErreur("");
    setF(client
      ? { nom: client.NOM, ville: client.VILLE, email: client.EMAIL, solde: String(client.SOLDE) }
      : VIDE);
  }, [ouvert, client]);

  const enregistrer = async () => {
    setEnCours(true);
    setErreur("");
    const fiche = { ...f, solde: Number(String(f.solde).replace(",", ".")) };
    try {
      const r = client ? await api.modifier(client.ID, fiche) : await api.creer(fiche);
      notifier("success", client ? "Client modifié" : "Client créé", r.NOM);
      onEnregistre();
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnCours(false);
    }
  };

  const champ = (cle, libelle, props = {}) => (
    <TextInput id={`fiche-${cle}`} labelText={libelle} value={f[cle]}
      onChange={(e) => setF({ ...f, [cle]: e.target.value })} {...props} />
  );

  return (
    <Modal
      open={ouvert}
      modalHeading={client ? `Modifier « ${client.NOM} »` : "Nouveau client"}
      modalLabel="DENOCRUD.CLIENTS"
      primaryButtonText={enCours ? "Enregistrement…" : "Enregistrer"}
      secondaryButtonText="Annuler"
      primaryButtonDisabled={enCours || !f.nom.trim()}
      onRequestClose={onFermer}
      onRequestSubmit={enregistrer}
    >
      <Stack gap={5}>
        {erreur && <InlineNotification kind="error" title="Refusé" subtitle={erreur} hideCloseButton lowContrast />}
        {champ("nom", "Nom", { maxLength: 60, "data-modal-primary-focus": true })}
        {champ("ville", "Ville", { maxLength: 40 })}
        {champ("email", "E-mail", { maxLength: 80, type: "email" })}
        {champ("solde", "Solde (€)", { inputMode: "decimal" })}
      </Stack>
    </Modal>
  );
}

/** Customer table: search, create, edit, delete. */
export default function Clients({ notifier }) {
  const [clients, setClients] = useState(null);
  const [q, setQ] = useState("");
  const [erreur, setErreur] = useState("");
  const [fiche, setFiche] = useState({ ouvert: false, client: null });
  const [aSupprimer, setASupprimer] = useState(null);
  const delai = useRef();

  const charger = useCallback(async (recherche) => {
    try {
      setErreur("");
      setClients(await api.clients(recherche));
    } catch (e) {
      setErreur(e.statut === 403 ? `Droits IBM i insuffisants : ${e.message}` : e.message);
      setClients([]);
    }
  }, []);

  useEffect(() => { charger(""); }, [charger]);

  const rechercher = (valeur) => {
    setQ(valeur);
    clearTimeout(delai.current);
    delai.current = setTimeout(() => charger(valeur), 300);
  };

  const supprimer = async () => {
    const c = aSupprimer;
    setASupprimer(null);
    try {
      await api.supprimer(c.ID);
      notifier("success", "Client supprimé", c.NOM);
      charger(q);
    } catch (e) {
      notifier("error", "Suppression refusée", e.message);
    }
  };

  const parId = new Map((clients ?? []).map((c) => [String(c.ID), c]));
  const lignes = (clients ?? []).map((c) => ({ ...c, id: String(c.ID), actions: "" }));

  return (
    <>
      {erreur && <InlineNotification kind="error" title="Erreur" subtitle={erreur} lowContrast onClose={() => setErreur("")} />}
      {clients === null ? (
        <DataTableSkeleton headers={ENTETES} rowCount={6} />
      ) : (
        <DataTable rows={lignes} headers={ENTETES} isSortable>
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps, getToolbarProps }) => (
            <TableContainer
              title="Clients"
              description={`DENOCRUD.CLIENTS sur IBMI · ${rows.length} client(s) · lectures et écritures sous votre profil IBM i`}
            >
              <TableToolbar {...getToolbarProps()}>
                <TableToolbarContent>
                  <TableToolbarSearch
                    persistent
                    placeholder="Rechercher un nom ou une ville"
                    value={q}
                    onChange={(e) => rechercher(e?.target?.value ?? "")}
                    onClear={() => rechercher("")}
                  />
                  <Button kind="ghost" hasIconOnly renderIcon={Renew} iconDescription="Actualiser" onClick={() => charger(q)} />
                  <Button renderIcon={Add} onClick={() => setFiche({ ouvert: true, client: null })}>
                    Nouveau client
                  </Button>
                </TableToolbarContent>
              </TableToolbar>
              <Table {...getTableProps()}>
                <TableHead>
                  <TableRow>
                    {headers.map((h) => (
                      <TableHeader key={h.key} {...getHeaderProps({ header: h, isSortable: h.key !== "actions" })}>
                        {h.header}
                      </TableHeader>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row) => {
                    const c = parId.get(row.id);
                    // DataTable keeps one render ahead with its old rows when the list changes
                    // (search): a row with no matching record is skipped
                    if (!c) return null;
                    return (
                      <TableRow key={row.id} {...getRowProps({ row })}>
                        {row.cells.map((cell) => {
                          const cle = cell.info.header;
                          if (cle === "SOLDE") {
                            return (
                              <TableCell key={cell.id} className={cell.value < 0 ? "negatif" : ""}>
                                {euros.format(cell.value)}
                              </TableCell>
                            );
                          }
                          if (cle === "actions") {
                            return (
                              <TableCell key={cell.id} className="cds--table-column-menu">
                                <OverflowMenu size="sm" flipped aria-label={`Actions sur ${c.NOM}`}>
                                  <OverflowMenuItem itemText="Modifier" onClick={() => setFiche({ ouvert: true, client: c })} />
                                  <OverflowMenuItem itemText="Supprimer" isDelete hasDivider onClick={() => setASupprimer(c)} />
                                </OverflowMenu>
                              </TableCell>
                            );
                          }
                          return <TableCell key={cell.id}>{cell.value}</TableCell>;
                        })}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DataTable>
      )}

      <Fiche
        ouvert={fiche.ouvert}
        client={fiche.client}
        notifier={notifier}
        onFermer={() => setFiche({ ouvert: false, client: null })}
        onEnregistre={() => { setFiche({ ouvert: false, client: null }); charger(q); }}
      />

      <Modal
        open={!!aSupprimer}
        danger
        modalHeading={aSupprimer ? `Supprimer « ${aSupprimer.NOM} » ?` : ""}
        modalLabel="DENOCRUD.CLIENTS"
        primaryButtonText="Supprimer"
        secondaryButtonText="Annuler"
        onRequestClose={() => setASupprimer(null)}
        onRequestSubmit={supprimer}
      >
        <p>La ligne est supprimée de Db2 for i, sous votre profil. Cette action est définitive.</p>
      </Modal>
    </>
  );
}
