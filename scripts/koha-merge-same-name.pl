#!/usr/bin/perl
# =============================================================================
# koha-merge-same-name.pl
# Fusiona patrones Koha con exactamente el mismo surname+firstname dentro de
# la misma categorycode. Regla: nombres iguales = misma persona.
#
# Lógica de destino:
#   - ESTUDI: destino = registro con cardnumber formato 20XXXXXXX/201XXXXXXX
#             (código estudiante gestionado por MidPoint).
#             Fuente = registro con cardnumber DNI u otro formato legacy.
#   - Resto (VISITA, DOCEN, ALUMNI, ADMINIST, STAFF):
#             destino = borrowernumber más bajo (registro más antiguo).
#
# Guardianes: NO fusiona si el destino tiene préstamos activos o deuda.
#
# USO:
#   sudo koha-shell bul -c "perl /tmp/koha-merge-same-name.pl --dry-run"
#   sudo koha-shell bul -c "perl /tmp/koha-merge-same-name.pl --dry-run --limit 20"
#   sudo koha-shell bul -c "perl /tmp/koha-merge-same-name.pl 2>&1 | tee /tmp/merge-same-name-$(date +%Y%m%d).log"
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
printf "=== koha-merge-same-name.pl === %s\n", $timestamp;
printf "Modo: %s\n", $dry_run ? 'DRY-RUN (sin cambios)' : '*** EJECUCION REAL ***';
printf "Limit: %s\n\n", defined $limit ? $limit : 'sin limite';

my $dbh = C4::Context->dbh;

# -------------------------------------------------------------------------
# Obtener grupos de duplicados por nombre exacto
# -------------------------------------------------------------------------
my $sql = q{
    SELECT
        categorycode,
        surname,
        firstname,
        COUNT(*) AS cnt,
        GROUP_CONCAT(borrowernumber ORDER BY borrowernumber SEPARATOR ',') AS bns,
        GROUP_CONCAT(COALESCE(cardnumber,'') ORDER BY borrowernumber SEPARATOR ',') AS cards
    FROM borrowers
    GROUP BY categorycode, surname, firstname
    HAVING COUNT(*) >= 2
    ORDER BY categorycode, COUNT(*) DESC, surname
};
$sql .= " LIMIT $limit" if defined $limit;

my $groups = $dbh->selectall_arrayref($sql, { Slice => {} });
printf "Grupos de duplicados encontrados: %d\n\n", scalar @$groups;

# -------------------------------------------------------------------------
# Contadores
# -------------------------------------------------------------------------
my ($merged_ok, $skipped_safety, $skipped_complex, $errors) = (0, 0, 0, 0);

for my $g (@$groups) {
    my @bns   = split /,/, $g->{bns};
    my @cards = split /,/, $g->{cards};
    my $cat   = $g->{categorycode};
    my $name  = sprintf('%s, %s', $g->{surname}, $g->{firstname});

    # Elegir destino según categoría
    my ($dest_bn, @source_bns);

    if ($cat eq 'ESTUDI' || $cat eq 'ALUMNI') {
        # Destino: el que tiene código estudiante (9 dígitos empezando en 20)
        my $midpoint_idx = -1;
        for my $i (0 .. $#cards) {
            if ($cards[$i] =~ /^20\d{7}$/) {
                $midpoint_idx = $i;
                last;
            }
        }
        if ($midpoint_idx >= 0) {
            $dest_bn    = $bns[$midpoint_idx];
            @source_bns = map { $bns[$_] } grep { $_ != $midpoint_idx } 0..$#bns;
        } else {
            # Ninguno tiene código MidPoint → destino = bn más bajo (índice 0)
            $dest_bn    = $bns[0];
            @source_bns = @bns[1..$#bns];
        }
    } else {
        # VISITA, DOCEN, ADMINIST, STAFF, etc: destino = bn más bajo
        $dest_bn    = $bns[0];
        @source_bns = @bns[1..$#bns];
    }

    my $info = sprintf('cat=%-8s dest_bn=%-6s | %s | cards=[%s]',
                       $cat, $dest_bn, $name, join(',', @cards));

    # Guardianes en el destino
    my ($activos, $deuda) = $dbh->selectrow_array(
        "SELECT
           (SELECT COUNT(*) FROM issues WHERE borrowernumber=?),
           (SELECT COALESCE(SUM(amountoutstanding),0) FROM accountlines WHERE borrowernumber=?)",
        undef, $dest_bn, $dest_bn
    );

    if ($activos > 0) {
        printf "SKIP-ACTIVOS  %s | dest tiene %d préstamos activos\n", $info, $activos;
        $skipped_safety++;
        next;
    }
    if ($deuda > 0) {
        printf "SKIP-DEUDA    %s | dest tiene deuda %.2f\n", $info, $deuda;
        $skipped_safety++;
        next;
    }

    if ($dry_run) {
        printf "DRY-RUN-MERGE %s | sources=[%s]\n", $info, join(',', @source_bns);
        $merged_ok++;
        next;
    }

    # Merge real
    eval {
        my $dest = Koha::Patrons->find($dest_bn);
        unless ($dest) {
            printf "SKIP-NOTFOUND %s | destino no encontrado\n", $info;
            $skipped_safety++;
            return;
        }
        $dest->merge_with(\@source_bns);
        printf "MERGED        %s | sources=[%s]\n", $info, join(',', @source_bns) if $verbose;
        $merged_ok++;
    };
    if ($@) {
        printf "ERROR         %s | %s\n", $info, $@;
        $errors++;
    }
}

# -------------------------------------------------------------------------
# Resumen
# -------------------------------------------------------------------------
printf "\n=== RESUMEN ===\n";
printf "%-25s %d\n", ($dry_run ? 'Para fusionar:' : 'Fusionados:'), $merged_ok;
printf "%-25s %d\n", 'Skip (seguridad):',    $skipped_safety;
printf "%-25s %d\n", 'Errores:',              $errors;
