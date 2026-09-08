# -*- coding: utf-8 -*-
# STeSI Consulting
# License OPL-1.
"""Mette al sicuro i conti predefiniti per contatto, in vista della 19.0.

`costs_account_id` e `revenues_account_id` sono `company_dependent`: nella 17.0
i loro valori stanno in `ir_property`, **non** nelle colonne omonime, che sono
rimaste da prima e non vengono nemmeno lette.

Nella 19.0 `ir.property` non esiste più — né il modello né la tabella — e i
valori vivono in colonne `jsonb` con l'id dell'azienda come chiave. La
conversione la fa il modulo, sul ramo 19.0, ma quello script gira **durante**
l'aggiornamento, quando `ir_property` può essere già stata eliminata:
l'aggiornamento del nucleo viene prima del nostro modulo, e la conversione
delle proprietà la fa il servizio di aggiornamento, il cui codice non sta nel
sorgente.

Per questo la copia si fa **adesso**, mentre il database è ancora alla 17.0 e le
proprietà ci sono. La tabella `stesi_revenues_costs_backup` non appartiene a
nessun modulo Odoo, quindi l'aggiornamento non la tocca.

Che cosa si perderebbe senza: su ogni fattura la riga prenderebbe il conto
predefinito del prodotto invece di quello del contatto, in silenzio. Sul
cliente sono **370 conti di costo e 196 di ricavo**.

Lo script è idempotente: rifà la copia ogni volta che gira.
"""
import logging

_logger = logging.getLogger(__name__)

COPIA = 'stesi_revenues_costs_backup'
CAMPI = ('costs_account_id', 'revenues_account_id')


def _esiste(cr, tabella):
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (tabella,))
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return  # installazione nuova: non c'è niente da salvare

    if not _esiste(cr, 'ir_property'):
        _logger.info("conti per contatto: ir_property non c'è, niente da copiare")
        return

    cr.execute("""
        SELECT count(*) FROM ir_property p
          JOIN ir_model_fields f ON f.id = p.fields_id
         WHERE f.model = 'res.partner' AND f.name IN %s
    """, (CAMPI,))
    quante = cr.fetchone()[0]
    if not quante:
        _logger.info("conti per contatto: nessuna proprietà da copiare")
        return

    cr.execute("DROP TABLE IF EXISTS %s" % COPIA)
    cr.execute("""
        CREATE TABLE {copia} AS
        SELECT f.name                                    AS campo,
               split_part(p.res_id, ',', 2)::integer     AS res_id,
               p.company_id                              AS company_id,
               split_part(p.value_reference, ',', 2)::integer AS valore
          FROM ir_property p
          JOIN ir_model_fields f ON f.id = p.fields_id
         WHERE f.model = 'res.partner'
           AND f.name IN %s
           AND p.res_id IS NOT NULL
           AND p.company_id IS NOT NULL
           AND p.value_reference IS NOT NULL
    """.format(copia=COPIA), (CAMPI,))
    cr.execute("CREATE INDEX %s_idx ON %s (campo, res_id, company_id)" % (COPIA, COPIA))

    cr.execute("SELECT campo, count(*) FROM %s GROUP BY 1 ORDER BY 1" % COPIA)
    for campo, quanti in cr.fetchall():
        _logger.info("conti per contatto: copiati %s valori di %s in %s",
                     quanti, campo, COPIA)

    cr.execute("SELECT count(*) FROM %s" % COPIA)
    copiate = cr.fetchone()[0]
    if copiate != quante:
        cr.execute("""
            SELECT count(*) FROM ir_property p
              JOIN ir_model_fields f ON f.id = p.fields_id
             WHERE f.model = 'res.partner' AND f.name IN %s AND p.res_id IS NULL
        """, (CAMPI,))
        default = cr.fetchone()[0]
        if default:
            _logger.error(
                "conti per contatto: %s proprietà sono default per azienda "
                "(res_id nullo) e NON sono nella copia: nella 19.0 servirebbe un "
                "ir.default. Vanno riportate a mano.", default)
        else:
            _logger.warning(
                "conti per contatto: copiate %s proprietà su %s; le altre non "
                "avevano un riferimento valido", copiate, quante)
