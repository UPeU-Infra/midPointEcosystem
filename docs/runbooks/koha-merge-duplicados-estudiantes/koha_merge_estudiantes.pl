#!/usr/bin/perl
#
# koha_merge_estudiantes.pl
# -----------------------------------------------------------------------------
# Fusión por lotes de cuentas Koha duplicadas (estudiante/egresado) en la
# instancia BUL de UPeU, usando el mecanismo NATIVO Koha::Patron->merge_with.
#
# Cada par = misma persona con DOS cuentas:
#   keeper = cuenta cuyo cardnumber es el CÓDIGO institucional (9-10 dígitos)
#   loser  = cuenta cuyo cardnumber es el DNI (8 dígitos)
# merge_with reasigna TODO el historial del loser al keeper y mueve el loser a
# deletedborrowers (NO hace DELETE crudo: preserva historial).
#
# SOLO afecta los pares de la lista de entrada (estudiantes/egresados puros).
# Los 16 pares trabajador YA FUERON EXCLUIDOS de la lista de entrada.
#
# USO:
#   # 1) DRY-RUN (por defecto, NO modifica nada):
#   sudo koha-shell bul -c "perl /ruta/koha_merge_estudiantes.pl --input /ruta/koha_merge_input_pares.tsv"
#
#   # 2) EJECUCIÓN REAL (requiere --commit explícito + backup previo):
#   sudo koha-shell bul -c "perl /ruta/koha_merge_estudiantes.pl --input /ruta/koha_merge_input_pares.tsv --commit"
#
# OPCIONES:
#   --input FILE     TSV de pares (obligatorio)
#   --commit         Ejecuta la fusión de verdad (sin esto = dry-run)
#   --batch N        Tamaño de lote (default 25); pausa entre lotes
#   --pause SECS     Pausa entre lotes en segundos (default 5)
#   --include-variant  Incluye también los pares STUDENT_NAME_VARIANT_REVIEW
#                      (por defecto se SALTAN y se marcan para revisión manual)
#   --only-dni DNI   Procesa solo ese DNI (para pruebas de un caso puntual)
#   --log FILE       Ruta del log (default ./koha_merge_YYYYMMDD_HHMMSS.log)
# -----------------------------------------------------------------------------

use Modern::Perl;
use Getopt::Long;
use POSIX qw(strftime);

use Koha::Patrons;
use Koha::Database;

# ---- args -------------------------------------------------------------------
my $input;
my $commit          = 0;
my $batch_size      = 25;
my $pause           = 5;
my $include_variant = 0;
my $only_dni        = '';
my $logfile         = '';
GetOptions(
    'input=s'         => \$input,
    'commit'          => \$commit,
    'batch=i'         => \$batch_size,
    'pause=i'         => \$pause,
    'include-variant' => \$include_variant,
    'only-dni=s'      => \$only_dni,
    'log=s'           => \$logfile,
) or die "Error en argumentos\n";

die "Falta --input FILE (TSV de pares)\n" unless $input && -f $input;

$logfile ||= 'koha_merge_' . strftime('%Y%m%d_%H%M%S', localtime) . '.log';
open(my $LOG, '>>', $logfile) or die "No puedo abrir log $logfile: $!\n";

sub logmsg {
    my ($msg) = @_;
    my $ts = strftime('%Y-%m-%d %H:%M:%S', localtime);
    say "$ts  $msg";
    say $LOG "$ts  $msg";
}

my $MODE = $commit ? 'COMMIT (REAL)' : 'DRY-RUN (sin cambios)';
logmsg("=============================================================");
logmsg("koha_merge_estudiantes.pl  -- MODO: $MODE");
logmsg("input=$input  batch=$batch_size  pause=${pause}s  include_variant=$include_variant"
        . ($only_dni ? "  only_dni=$only_dni" : ""));
logmsg("=============================================================");

# ---- leer TSV ---------------------------------------------------------------
open(my $IN, '<', $input) or die "No puedo abrir $input: $!\n";
my $header = <$IN>;
chomp $header;
my @cols = split /\t/, $header;
my %idx;
@idx{@cols} = 0 .. $#cols;
for my $req (qw(keeper_borrowernumber loser_borrowernumber dni keeper_cardnumber loser_cardnumber category)) {
    die "Columna requerida '$req' no está en el TSV\n" unless exists $idx{$req};
}

my @pairs;
while (my $line = <$IN>) {
    chomp $line;
    next unless length $line;
    my @f = split /\t/, $line, -1;
    push @pairs, {
        keeper        => $f[$idx{keeper_borrowernumber}],
        loser         => $f[$idx{loser_borrowernumber}],
        dni           => $f[$idx{dni}],
        keeper_card   => $f[$idx{keeper_cardnumber}],
        loser_card    => $f[$idx{loser_cardnumber}],
        keeper_name   => exists $idx{keeper_name} ? $f[$idx{keeper_name}] : '',
        loser_name    => exists $idx{loser_name}  ? $f[$idx{loser_name}]  : '',
        category      => $f[$idx{category}],
        has_historial => exists $idx{has_historial} ? $f[$idx{has_historial}] : '?',
        mp_points_to  => exists $idx{mp_points_to}  ? $f[$idx{mp_points_to}]  : '?',
    };
}
close $IN;
logmsg("Pares leídos del TSV: " . scalar(@pairs));

# ---- contadores -------------------------------------------------------------
my ($n_ok, $n_skip, $n_fail, $n_processed) = (0,0,0,0);
my @review;

my $schema = Koha::Database->new->schema;

# ---- procesar por lotes -----------------------------------------------------
my $i = 0;
for my $p (@pairs) {
    $i++;

    if ($only_dni && $p->{dni} ne $only_dni) { next; }

    # ---- validaciones pre-merge ----
    my $tag = sprintf("DNI=%s keeper_bn=%s(card=%s) loser_bn=%s(card=%s) [%s] hist=%s MP=%s name='%s'",
        $p->{dni}, $p->{keeper}, $p->{keeper_card}, $p->{loser}, $p->{loser_card},
        $p->{category}, $p->{has_historial}, $p->{mp_points_to}, $p->{keeper_name});

    # nunca tocar trabajadores (no deberían estar en el TSV, pero por seguridad)
    if ($p->{category} eq 'WORKER_EXCLUDE') {
        logmsg("SKIP (worker, excluido) -> $tag");
        $n_skip++; next;
    }

    # name-variant: por defecto se salta y se marca para revisión manual
    if ($p->{category} eq 'STUDENT_NAME_VARIANT_REVIEW' && !$include_variant) {
        logmsg("SKIP (name-variant, revisar manualmente) -> $tag");
        push @review, $tag;
        $n_skip++; next;
    }

    # keeper card debe ser código 9-10 dígitos; loser card debe ser DNI 8 dígitos == dni
    unless ($p->{keeper_card} =~ /^\d{9,10}$/) {
        logmsg("SKIP (keeper card NO parece código 9-10 díg) -> $tag");
        push @review, "keeper_card_invalido: $tag";
        $n_skip++; next;
    }
    unless ($p->{loser_card} =~ /^\d{8}$/ && $p->{loser_card} eq $p->{dni}) {
        logmsg("SKIP (loser card NO es DNI de 8 díg / no coincide con dni) -> $tag");
        push @review, "loser_card_invalido: $tag";
        $n_skip++; next;
    }

    # ---- cargar patrones reales y revalidar contra la DB viva ----
    my $keeper = Koha::Patrons->find($p->{keeper});
    my $loser  = Koha::Patrons->find($p->{loser});

    unless ($keeper) { logmsg("SKIP (keeper no existe en DB) -> $tag"); $n_skip++; next; }
    unless ($loser)  { logmsg("SKIP (loser no existe en DB)  -> $tag"); $n_skip++; next; }

    # revalidar cardnumbers contra DB viva (los conteos podrían haber cambiado)
    if ($keeper->cardnumber ne $p->{keeper_card}) {
        logmsg("SKIP (keeper.cardnumber DB='".$keeper->cardnumber."' != TSV) -> $tag");
        push @review, "drift_keeper_card: $tag"; $n_skip++; next;
    }
    if ($loser->cardnumber ne $p->{loser_card}) {
        logmsg("SKIP (loser.cardnumber DB='".$loser->cardnumber."' != TSV) -> $tag");
        push @review, "drift_loser_card: $tag"; $n_skip++; next;
    }

    # no fusionar protegidos
    if ($keeper->protected) { logmsg("SKIP (keeper protegido) -> $tag"); $n_skip++; next; }
    if ($loser->protected)  { logmsg("SKIP (loser protegido)  -> $tag"); $n_skip++; next; }

    # salvaguarda anti-DNI: keeper NO debe ser el de cardnumber=DNI
    if ($keeper->cardnumber =~ /^\d{8}$/ && $keeper->cardnumber eq $p->{dni}) {
        logmsg("SKIP (SALVAGUARDA: keeper tiene cardnumber=DNI; no debe ser keeper) -> $tag");
        push @review, "keeper_es_DNI: $tag"; $n_skip++; next;
    }

    # ---- contar transacciones que se moverían (informativo) ----
    my $moved =
          $schema->resultset('Issue')->search({ borrowernumber => $loser->id })->count
        + $schema->resultset('OldIssue')->search({ borrowernumber => $loser->id })->count
        + $schema->resultset('Reserve')->search({ borrowernumber => $loser->id })->count
        + $schema->resultset('OldReserve')->search({ borrowernumber => $loser->id })->count
        + $schema->resultset('Accountline')->search({ borrowernumber => $loser->id })->count;

    # advertencia SSO: keeper debería conservar email institucional
    my $kmail = $keeper->email // '';
    my $warn_mail = ($kmail =~ /\@upeu\.edu\.pe$/i) ? '' : ' [WARN: keeper sin email @upeu.edu.pe -> revisar SSO/Keycloak]';

    $n_processed++;

    if (!$commit) {
        logmsg("DRY-RUN merge_with: keeper=".$keeper->id." <- loser=".$loser->id
            ." | moverian ~$moved transacciones | keeper_email='$kmail'$warn_mail | $tag");
        $n_ok++;
    }
    else {
        my $rc = eval {
            $keeper->merge_with([ $loser->id ]);
            1;
        };
        if ($rc) {
            logmsg("OK merge_with: keeper=".$keeper->id." <- loser=".$loser->id
                ." | movidas ~$moved transacciones | keeper_email='$kmail'$warn_mail | $tag");
            $n_ok++;
        }
        else {
            logmsg("FAIL merge_with: keeper=".$keeper->id." <- loser=".$loser->id." ERROR: $@ | $tag");
            $n_fail++;
        }
    }

    # ---- pausa por lote ----
    if ($n_processed % $batch_size == 0) {
        logmsg(">>> Lote de $batch_size completado (procesados=$n_processed). Pausa ${pause}s...");
        sleep $pause unless !$commit && $pause == 0;
    }
}

# ---- resumen ----------------------------------------------------------------
logmsg("=============================================================");
logmsg("RESUMEN ($MODE):  ok=$n_ok  skip=$n_skip  fail=$n_fail  procesados=$n_processed");
if (@review) {
    logmsg("PARES PARA REVISIÓN MANUAL (" . scalar(@review) . "):");
    logmsg("   $_") for @review;
}
logmsg("Log: $logfile");
logmsg("=============================================================");
close $LOG;
