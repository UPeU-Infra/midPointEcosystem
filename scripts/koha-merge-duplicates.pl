#!/usr/bin/perl
# =============================================================================
# koha-merge-duplicates.pl
# Fusiona patrones duplicados en Koha: absorbe el patron estudiantil (ESTUDI/
# PREGRADO/POSGRADO/ALUMNI con cardnumber = código universitario) en el patron
# canónico gobernado por MidPoint (ADMINIST/DOCEN con cardnumber = DNI).
#
# Requiere ejecución dentro del contexto de la instancia Koha "bul":
#
#   koha-shell bul -c "perl /usr/share/koha/scripts/koha-merge-duplicates.pl --dry-run"
#   koha-shell bul -c "perl /usr/share/koha/scripts/koha-merge-duplicates.pl --limit 5"
#   koha-shell bul -c "perl /usr/share/koha/scripts/koha-merge-duplicates.pl 2>&1 | tee /tmp/merge-log-\$(date +%Y%m%d).txt"
#
# Opciones:
#   --dry-run      Solo reportar pares, sin ejecutar merge
#   --limit N      Procesar máximo N pares distintos de (origen,destino)
#   --pair SRC,DST Procesar solo este par de borrowernumbers (ej: 3144,30303)
#   --verbose      Mostrar detalle de tablas actualizadas por cada merge
# =============================================================================
use strict;
use warnings;
use Getopt::Long;
use C4::Context;
use Koha::Patrons;

# ---------------------------------------------------------------------------
# Opciones de línea de comandos
# ---------------------------------------------------------------------------
my ($dry_run, $limit, $pair_arg, $verbose) = (0, undef, undef, 0);
GetOptions(
    'dry-run'   => \$dry_run,
    'limit=i'   => \$limit,
    'pair=s'    => \$pair_arg,
    'verbose'   => \$verbose,
) or die "Uso: $0 [--dry-run] [--limit N] [--pair SRC,DST] [--verbose]\n";

# ---------------------------------------------------------------------------
# Conexión a la base de datos
# ---------------------------------------------------------------------------
my $dbh = C4::Context->dbh;

# ---------------------------------------------------------------------------
# Obtener pares duplicados
# ---------------------------------------------------------------------------
my @pairs;

if ($pair_arg) {
    # Modo par individual: --pair 3144,30303
    my ($bn_src, $bn_dst) = split /,/, $pair_arg;
    die "Formato inválido para --pair. Usar: --pair SRC,DST\n"
        unless $bn_src && $bn_dst && $bn_src =~ /^\d+$/ && $bn_dst =~ /^\d+$/;

    my $sql_pair = q{
        SELECT
            b_est.borrowernumber  AS bn_origen,
            b_est.cardnumber      AS card_origen,
            b_est.categorycode    AS cat_origen,
            b_dni.borrowernumber  AS bn_destino,
            b_dni.cardnumber      AS card_destino,
            b_dni.categorycode    AS cat_destino,
            b_dni.surname, b_dni.firstname,
            (SELECT COUNT(*) FROM old_issues WHERE borrowernumber = b_est.borrowernumber) AS prestamos_hist,
            (SELECT COUNT(*) FROM issues       WHERE borrowernumber = b_est.borrowernumber) AS prestamos_activos
        FROM borrowers b_est
        JOIN borrowers b_dni ON b_dni.borrowernumber = ?
        WHERE b_est.borrowernumber = ?
    };
    my $row = $dbh->selectrow_hashref($sql_pair, undef, $bn_dst, $bn_src);
    die "No se encontró el par $bn_src → $bn_dst en la base de datos.\n" unless $row;
    push @pairs, $row;
} else {
    # Modo batch: buscar todos los pares por nombre+apellido
    my $sql = q{
        SELECT
            b_est.borrowernumber  AS bn_origen,
            b_est.cardnumber      AS card_origen,
            b_est.categorycode    AS cat_origen,
            b_dni.borrowernumber  AS bn_destino,
            b_dni.cardnumber      AS card_destino,
            b_dni.categorycode    AS cat_destino,
            b_dni.surname, b_dni.firstname,
            (SELECT COUNT(*) FROM old_issues WHERE borrowernumber = b_est.borrowernumber) AS prestamos_hist,
            (SELECT COUNT(*) FROM issues       WHERE borrowernumber = b_est.borrowernumber) AS prestamos_activos
        FROM borrowers b_est
        JOIN borrowers b_dni
            ON  b_est.surname    = b_dni.surname
            AND b_est.firstname  = b_dni.firstname
            AND b_est.borrowernumber != b_dni.borrowernumber
        WHERE b_est.categorycode IN ('PREGRADO','POSGRADO','ALUMNI','ESTUDI')
          AND b_dni.categorycode  IN ('ADMINIST','DOCEN')
        ORDER BY b_dni.surname, b_dni.firstname
    };
    $sql .= " LIMIT $limit" if defined $limit;

    my $rows = $dbh->selectall_arrayref($sql, { Slice => {} });
    @pairs = @$rows;
}

# ---------------------------------------------------------------------------
# Resumen inicial
# ---------------------------------------------------------------------------
my $total = scalar @pairs;
my $con_hist = grep { $_->{prestamos_hist} > 0 || $_->{prestamos_activos} > 0 } @pairs;
my $total_hist = 0;
my $total_activos = 0;
$total_hist    += $_->{prestamos_hist}    for @pairs;
$total_activos += $_->{prestamos_activos} for @pairs;

printf "=" x 70 . "\n";
printf "koha-merge-duplicates.pl — Koha BUL\n";
printf "=" x 70 . "\n";
printf "Modo           : %s\n", $dry_run ? 'DRY-RUN (sin cambios)' : 'EJECUCION REAL';
printf "Pares encontrados: %d\n", $total;
printf "Con préstamos históricos a preservar: %d (%d préstamos, %d activos)\n",
    $con_hist, $total_hist, $total_activos;
printf "=" x 70 . "\n\n";

# ---------------------------------------------------------------------------
# Procesamiento de pares
# ---------------------------------------------------------------------------
my ($ok, $err, $skip) = (0, 0, 0);
my @errores;

for my $pair (@pairs) {
    printf "[%s → %s] %-30s %-20s  (cat: %-8s → %-8s)  hist=%d  activos=%d\n",
        $pair->{card_origen}  // 'NULL',
        $pair->{card_destino} // 'NULL',
        substr("$pair->{surname},", 0, 29),
        substr($pair->{firstname}, 0, 19),
        $pair->{cat_origen},
        $pair->{cat_destino},
        $pair->{prestamos_hist},
        $pair->{prestamos_activos};

    if ($dry_run) {
        $ok++;
        next;
    }

    # Guardar nota en el patron destino antes del merge (trazabilidad)
    my $nota = sprintf(
        "[MERGE %s] Absorbido patron bn=%d card=%s cat=%s con %d prest.hist.",
        scalar localtime,
        $pair->{bn_origen},
        $pair->{card_origen} // 'NULL',
        $pair->{cat_origen},
        $pair->{prestamos_hist}
    );

    eval {
        my $destino = Koha::Patrons->find($pair->{bn_destino});
        my $origen  = Koha::Patrons->find($pair->{bn_origen});

        unless ($destino) {
            warn "  SKIP: patron destino bn=$pair->{bn_destino} no encontrado\n";
            $skip++;
            return;  # next iteration
        }
        unless ($origen) {
            warn "  SKIP: patron origen bn=$pair->{bn_origen} no encontrado\n";
            $skip++;
            return;
        }

        if ($destino->is_anonymous || $destino->protected) {
            warn "  SKIP: patron destino es anonymous o protected\n";
            $skip++;
            return;
        }
        if ($origen->is_anonymous || $origen->protected) {
            warn "  SKIP: patron origen es anonymous o protected\n";
            $skip++;
            return;
        }

        # Verificar que el destino no tiene préstamos activos bloqueantes
        if ($pair->{prestamos_activos} > 0) {
            warn "  ADVERTENCIA: el origen tiene $pair->{prestamos_activos} préstamo(s) activo(s).\n";
            warn "               Se trasladarán al patron destino por el merge.\n";
        }

        # Agregar nota interna de trazabilidad al patron destino
        my $nota_actual = $destino->borrowernotes // '';
        $destino->set({ borrowernotes => ($nota_actual ? "$nota_actual\n$nota" : $nota) })->store;

        # Ejecutar el merge: el destino absorbe al origen
        my $results = $destino->merge_with([ $pair->{bn_origen} ]);

        if ($verbose && $results) {
            for my $merged_id (keys %{ $results->{merged} }) {
                printf "  Tablas actualizadas para bn=%d:\n", $merged_id;
                for my $table (keys %{ $results->{merged}{$merged_id}{updated} }) {
                    printf "    %-40s %d filas\n",
                        $table, $results->{merged}{$merged_id}{updated}{$table};
                }
            }
        }

        printf "  OK: bn=%d absorbido en bn=%d\n",
            $pair->{bn_origen}, $pair->{bn_destino};
        $ok++;
    };
    if ($@) {
        my $err_msg = $@;
        $err_msg =~ s/\n/ /g;
        warn "  ERROR: $err_msg\n";
        push @errores, {
            bn_origen  => $pair->{bn_origen},
            bn_destino => $pair->{bn_destino},
            error      => $err_msg,
        };
        $err++;
    }
}

# ---------------------------------------------------------------------------
# Resumen final
# ---------------------------------------------------------------------------
printf "\n" . "=" x 70 . "\n";
printf "RESUMEN FINAL\n";
printf "=" x 70 . "\n";
printf "OK      : %d\n", $ok;
printf "ERRORES : %d\n", $err;
printf "SKIP    : %d\n", $skip;
printf "Total   : %d\n", $ok + $err + $skip;

if (@errores) {
    printf "\nPares con error:\n";
    for my $e (@errores) {
        printf "  bn_origen=%-6d → bn_destino=%-6d  %s\n",
            $e->{bn_origen}, $e->{bn_destino}, $e->{error};
    }
}

printf "\n";
exit( $err > 0 ? 1 : 0 );
