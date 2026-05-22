#!/usr/bin/perl
# =============================================================================
# koha-delete-nocardnumber.pl
# Elimina patrones Koha creados por MidPoint sin cardnumber asignado.
#
# Criterios de selección (todos deben cumplirse):
#   - cardnumber IS NULL o vacío
#   - userid con formato nombre.apellido (contiene punto, sin espacios)
#   - date_enrolled >= 2026-03-19 (primer import masivo MidPoint)
#   - categorycode IN ('PREGRADO','POSGRADO','ESTUDI','ALUMNI','ADMINIST','DOCEN')
#   - SIN préstamos activos (issues)
#   - SIN préstamos históricos (old_issues)
#   - SIN multas pendientes (account_lines con amountoutstanding > 0)
#
# Koha::Patron->delete() mueve el patron a deletedborrowers — NO es hard delete.
# Los datos son recuperables por DBA via: INSERT INTO borrowers SELECT * FROM deletedborrowers WHERE ...
#
# USO:
#   sudo koha-shell bul -c "perl /tmp/koha-delete-nocardnumber.pl --dry-run"
#   sudo koha-shell bul -c "perl /tmp/koha-delete-nocardnumber.pl --dry-run --limit 20"
#   sudo koha-shell bul -c "perl /tmp/koha-delete-nocardnumber.pl --limit 50"
#   sudo koha-shell bul -c "perl /tmp/koha-delete-nocardnumber.pl 2>&1 | tee /tmp/delete-nocardnumber-$(date +%Y%m%d).log"
#
# PREREQUISITO: siempre ejecutar --dry-run primero y revisar el output.
# =============================================================================

use strict;
use warnings;
use Getopt::Long;
use POSIX qw(strftime);

use C4::Context;
use Koha::Patrons;

my ($dry_run, $limit, $verbose) = (0, undef, 0);
GetOptions(
    'dry-run'   => \$dry_run,
    'limit=i'   => \$limit,
    'verbose'   => \$verbose,
);

my $timestamp = strftime('%Y-%m-%d %H:%M:%S', localtime);
printf "=== koha-delete-nocardnumber.pl === %s\n", $timestamp;
printf "Modo: %s\n", $dry_run ? 'DRY-RUN (sin cambios)' : '*** EJECUCION REAL ***';
printf "Limit: %s\n\n", defined $limit ? $limit : 'sin limite';

my $dbh = C4::Context->dbh;

# -------------------------------------------------------------------------
# Selección de candidatos
# -------------------------------------------------------------------------
my $sql = q{
    SELECT
        b.borrowernumber,
        b.cardnumber,
        b.userid,
        b.surname,
        b.firstname,
        b.categorycode,
        b.date_enrolled,
        b.dateexpiry,
        (SELECT COUNT(*) FROM issues      WHERE borrowernumber = b.borrowernumber) AS activos,
        (SELECT COUNT(*) FROM old_issues  WHERE borrowernumber = b.borrowernumber) AS historicos,
        (SELECT COALESCE(SUM(amountoutstanding),0)
           FROM account_lines             WHERE borrowernumber = b.borrowernumber) AS deuda
    FROM borrowers b
    WHERE (b.cardnumber IS NULL OR b.cardnumber = '')
      AND b.userid REGEXP '^[a-zA-Z][a-zA-ZáéíóúÁÉÍÓÚñÑ]+\\.[a-zA-ZáéíóúÁÉÍÓÚñÑ]'
      AND b.date_enrolled >= '2026-03-19'
      AND b.categorycode IN ('PREGRADO','POSGRADO','ESTUDI','ALUMNI','ADMINIST','DOCEN','STAFF')
    ORDER BY b.borrowernumber
};
$sql .= " LIMIT $limit" if defined $limit;

my $candidates = $dbh->selectall_arrayref($sql, { Slice => {} });
printf "Candidatos encontrados: %d\n\n", scalar @$candidates;

# -------------------------------------------------------------------------
# Contadores
# -------------------------------------------------------------------------
my ($deleted, $skipped_loans, $skipped_debt, $skipped_history, $errors) = (0,0,0,0,0);

for my $c (@$candidates) {
    my $bn   = $c->{borrowernumber};
    my $name = sprintf('%s, %s', $c->{surname} // '', $c->{firstname} // '');
    my $info = sprintf('bn=%-6s | cat=%-8s | userid=%-30s | enrolled=%s',
                       $bn, $c->{categorycode}, $c->{userid} // '', $c->{date_enrolled} // '');

    # Guardianes de seguridad
    if ($c->{activos} > 0) {
        printf "SKIP-ACTIVOS    %s | prestamos_activos=%d\n", $info, $c->{activos};
        $skipped_loans++;
        next;
    }
    if ($c->{deuda} > 0) {
        printf "SKIP-DEUDA      %s | deuda=%.2f\n", $info, $c->{deuda};
        $skipped_debt++;
        next;
    }
    if ($c->{historicos} > 0) {
        printf "SKIP-HISTORICOS %s | prestamos_hist=%d\n", $info, $c->{historicos};
        $skipped_history++;
        next;
    }

    if ($dry_run) {
        printf "DRY-RUN-DELETE  %s | %s\n", $info, $name;
        $deleted++;
        next;
    }

    # Eliminación real
    eval {
        my $patron = Koha::Patrons->find($bn);
        unless ($patron) {
            printf "SKIP-NOTFOUND   %s\n", $info;
            $skipped_loans++;
            return;
        }
        $patron->delete();
        printf "DELETED         %s | %s\n", $info, $name if $verbose;
        $deleted++;
    };
    if ($@) {
        printf "ERROR           %s | %s\n", $info, $@;
        $errors++;
    }
}

# -------------------------------------------------------------------------
# Resumen final
# -------------------------------------------------------------------------
printf "\n=== RESUMEN ===\n";
printf "%-25s %d\n", ($dry_run ? 'Para eliminar:' : 'Eliminados:'),   $deleted;
printf "%-25s %d\n", 'Skip (préstamos activos):',  $skipped_loans;
printf "%-25s %d\n", 'Skip (deuda pendiente):',    $skipped_debt;
printf "%-25s %d\n", 'Skip (historial préstamos):',  $skipped_history;
printf "%-25s %d\n", 'Errores:',                   $errors;
printf "\nNota: los registros eliminados quedan en la tabla deletedborrowers (recuperables).\n" unless $dry_run;
