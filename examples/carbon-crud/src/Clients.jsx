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

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "EUR" });
// keys: Db2 columns of DENOCRUD.CLIENTS (IBM i object, unchanged)
const HEADERS = [
  { key: "NOM", header: "Name" },
  { key: "VILLE", header: "City" },
  { key: "EMAIL", header: "E-mail" },
  { key: "SOLDE", header: "Balance" },
  { key: "MAJ_PAR", header: "Changed by" },
  { key: "MAJ_LE", header: "Changed on" },
  { key: "actions", header: "" },
];
// keys: JSON fields of the API (unchanged)
const EMPTY_RECORD = { nom: "", ville: "", email: "", solde: "0" };

/** Dialog for creating or editing a customer. */
function CustomerDialog({ open, customer, onClose, onSaved, notify }) {
  const [form, setForm] = useState(EMPTY_RECORD);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError("");
    setForm(customer
      ? { nom: customer.NOM, ville: customer.VILLE, email: customer.EMAIL, solde: String(customer.SOLDE) }
      : EMPTY_RECORD);
  }, [open, customer]);

  const save = async () => {
    setBusy(true);
    setError("");
    const record = { ...form, solde: Number(String(form.solde).replace(",", ".")) };
    try {
      const r = customer ? await api.update(customer.ID, record) : await api.create(record);
      notify("success", customer ? "Customer updated" : "Customer created", r.NOM);
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const field = (key, label, props = {}) => (
    <TextInput id={`record-${key}`} labelText={label} value={form[key]}
      onChange={(e) => setForm({ ...form, [key]: e.target.value })} {...props} />
  );

  return (
    <Modal
      open={open}
      modalHeading={customer ? `Edit "${customer.NOM}"` : "New customer"}
      modalLabel="DENOCRUD.CLIENTS"
      primaryButtonText={busy ? "Saving…" : "Save"}
      secondaryButtonText="Cancel"
      primaryButtonDisabled={busy || !form.nom.trim()}
      onRequestClose={onClose}
      onRequestSubmit={save}
    >
      <Stack gap={5}>
        {error && <InlineNotification kind="error" title="Refused" subtitle={error} hideCloseButton lowContrast />}
        {field("nom", "Name", { maxLength: 60, "data-modal-primary-focus": true })}
        {field("ville", "City", { maxLength: 40 })}
        {field("email", "E-mail", { maxLength: 80, type: "email" })}
        {field("solde", "Balance (€)", { inputMode: "decimal" })}
      </Stack>
    </Modal>
  );
}

/** Customer table: search, create, edit, delete. */
export default function Clients({ notify }) {
  const [customers, setCustomers] = useState(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState({ open: false, customer: null });
  const [pendingDelete, setPendingDelete] = useState(null);
  const debounce = useRef();

  const load = useCallback(async (search) => {
    try {
      setError("");
      setCustomers(await api.customers(search));
    } catch (e) {
      setError(e.status === 403 ? `Insufficient IBM i authority: ${e.message}` : e.message);
      setCustomers([]);
    }
  }, []);

  useEffect(() => { load(""); }, [load]);

  const search = (value) => {
    setQ(value);
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => load(value), 300);
  };

  const remove = async () => {
    const c = pendingDelete;
    setPendingDelete(null);
    try {
      await api.remove(c.ID);
      notify("success", "Customer deleted", c.NOM);
      load(q);
    } catch (e) {
      notify("error", "Delete refused", e.message);
    }
  };

  const byId = new Map((customers ?? []).map((c) => [String(c.ID), c]));
  const tableRows = (customers ?? []).map((c) => ({ ...c, id: String(c.ID), actions: "" }));

  return (
    <>
      {error && <InlineNotification kind="error" title="Error" subtitle={error} lowContrast onClose={() => setError("")} />}
      {customers === null ? (
        <DataTableSkeleton headers={HEADERS} rowCount={6} />
      ) : (
        <DataTable rows={tableRows} headers={HEADERS} isSortable>
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps, getToolbarProps }) => (
            <TableContainer
              title="Customers"
              description={`DENOCRUD.CLIENTS on IBMI · ${rows.length} customer(s) · reads and writes run under your IBM i profile`}
            >
              <TableToolbar {...getToolbarProps()}>
                <TableToolbarContent>
                  <TableToolbarSearch
                    persistent
                    placeholder="Search a name or a city"
                    value={q}
                    onChange={(e) => search(e?.target?.value ?? "")}
                    onClear={() => search("")}
                  />
                  <Button kind="ghost" hasIconOnly renderIcon={Renew} iconDescription="Refresh" onClick={() => load(q)} />
                  <Button renderIcon={Add} onClick={() => setDialog({ open: true, customer: null })}>
                    New customer
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
                    const c = byId.get(row.id);
                    // DataTable keeps one render ahead with its old rows when the list changes
                    // (search): a row with no matching record is skipped
                    if (!c) return null;
                    return (
                      <TableRow key={row.id} {...getRowProps({ row })}>
                        {row.cells.map((cell) => {
                          const columnKey = cell.info.header;
                          if (columnKey === "SOLDE") {
                            return (
                              <TableCell key={cell.id} className={cell.value < 0 ? "negative" : ""}>
                                {currency.format(cell.value)}
                              </TableCell>
                            );
                          }
                          if (columnKey === "actions") {
                            return (
                              <TableCell key={cell.id} className="cds--table-column-menu">
                                <OverflowMenu size="sm" flipped aria-label={`Actions for ${c.NOM}`}>
                                  <OverflowMenuItem itemText="Edit" onClick={() => setDialog({ open: true, customer: c })} />
                                  <OverflowMenuItem itemText="Delete" isDelete hasDivider onClick={() => setPendingDelete(c)} />
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

      <CustomerDialog
        open={dialog.open}
        customer={dialog.customer}
        notify={notify}
        onClose={() => setDialog({ open: false, customer: null })}
        onSaved={() => { setDialog({ open: false, customer: null }); load(q); }}
      />

      <Modal
        open={!!pendingDelete}
        danger
        modalHeading={pendingDelete ? `Delete "${pendingDelete.NOM}"?` : ""}
        modalLabel="DENOCRUD.CLIENTS"
        primaryButtonText="Delete"
        secondaryButtonText="Cancel"
        onRequestClose={() => setPendingDelete(null)}
        onRequestSubmit={remove}
      >
        <p>The row is deleted from Db2 for i, under your profile. This cannot be undone.</p>
      </Modal>
    </>
  );
}
