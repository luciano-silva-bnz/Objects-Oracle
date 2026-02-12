<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/config/bootstrap.php';

const SCANNTECH_MINORISTA_FIXO = 58693;

$estado = isset($_GET['estado']) && trim((string) $_GET['estado']) !== ''
    ? strtoupper(trim((string) $_GET['estado']))
    : 'ACEPTADA';

$op = isset($_GET['op']) ? strtolower(trim((string) $_GET['op'])) : 'and';
if ($op !== 'and' && $op !== 'or') {
    $op = 'and';
}

$filiais = parse_filiais_param($_GET['filiais'] ?? null);
if ($filiais === []) {
    $filiais = app_read_filiais(app_project_path('storage/filiais.json'));
}

if ($filiais === []) {
    app_json_response(
        [
            'meta' => [
                'minorista' => SCANNTECH_MINORISTA_FIXO,
                'filiaisSolicitadas' => [],
                'filiaisComErro' => [],
                'totalPromocoes' => 0,
                'atualizadoEm' => date(DATE_ATOM),
            ],
            'data' => [],
            'error' => 'Nenhuma filial disponivel para consulta.',
        ],
        400
    );
    exit;
}

$baseUrl = rtrim((string) app_env('SCANNTECH_BASE_URL', 'http://parceiro.scanntech.com/pmkt-rest-api/v2'), '/');
$username = (string) app_env('SCANNTECH_USER', '');
$password = (string) app_env('SCANNTECH_PASS', '');

if ($username === '' || $password === '') {
    app_json_response(
        [
            'meta' => [
                'minorista' => SCANNTECH_MINORISTA_FIXO,
                'filiaisSolicitadas' => $filiais,
                'filiaisComErro' => [],
                'totalPromocoes' => 0,
                'atualizadoEm' => date(DATE_ATOM),
            ],
            'data' => [],
            'error' => 'Credenciais nao configuradas. Defina SCANNTECH_USER e SCANNTECH_PASS.',
        ],
        500
    );
    exit;
}

$timeout = max(5, (int) app_env('REQUEST_TIMEOUT', '20'));
$cacheTtl = max(0, (int) app_env('CACHE_TTL', '120'));
$cacheDir = app_project_path('storage/cache');

$promocoes = [];
$filiaisComErro = [];
$filiaisComSucesso = [];

foreach ($filiais as $filial) {
    try {
        $payload = fetch_promocoes_por_filial(
            $filial,
            $estado,
            $baseUrl,
            $username,
            $password,
            $timeout,
            $cacheDir,
            $cacheTtl
        );

        $promocoesDaFilial = normalize_promocoes((array) $payload, $filial);
        $promocoes = array_merge($promocoes, $promocoesDaFilial);
        $filiaisComSucesso[] = $filial;
    } catch (RuntimeException $exception) {
        $filiaisComErro[] = [
            'filial' => $filial,
            'status' => $exception->getCode() > 0 ? $exception->getCode() : 0,
            'mensagem' => $exception->getMessage(),
        ];
    }
}

usort(
    $promocoes,
    static function (array $left, array $right): int {
        $byFilial = ($left['filial'] ?? 0) <=> ($right['filial'] ?? 0);
        if ($byFilial !== 0) {
            return $byFilial;
        }

        return strcmp((string) ($left['titulo'] ?? ''), (string) ($right['titulo'] ?? ''));
    }
);

app_json_response(
    [
        'meta' => [
            'minorista' => SCANNTECH_MINORISTA_FIXO,
            'estado' => $estado,
            'operador' => $op,
            'filiaisSolicitadas' => $filiais,
            'filiaisComSucesso' => $filiaisComSucesso,
            'filiaisComErro' => $filiaisComErro,
            'totalPromocoes' => count($promocoes),
            'atualizadoEm' => date(DATE_ATOM),
        ],
        'data' => $promocoes,
    ]
);

function parse_filiais_param(mixed $rawFiliais): array
{
    if ($rawFiliais === null) {
        return [];
    }

    $parts = preg_split('/[\s,;]+/', (string) $rawFiliais, -1, PREG_SPLIT_NO_EMPTY);
    if ($parts === false) {
        return [];
    }

    return app_normalize_int_list($parts);
}

/**
 * @return array<string, mixed>
 */
function fetch_promocoes_por_filial(
    int $filial,
    string $estado,
    string $baseUrl,
    string $username,
    string $password,
    int $timeout,
    string $cacheDir,
    int $cacheTtl
): array {
    $cacheFile = rtrim($cacheDir, '/\\') . DIRECTORY_SEPARATOR . sprintf(
        'filial_%d_estado_%s.json',
        $filial,
        preg_replace('/[^A-Za-z0-9_-]/', '_', $estado) ?? 'ACEPTADA'
    );

    if ($cacheTtl > 0 && is_file($cacheFile)) {
        $cacheAge = time() - (int) filemtime($cacheFile);
        if ($cacheAge >= 0 && $cacheAge <= $cacheTtl) {
            $cachedRaw = file_get_contents($cacheFile);
            if ($cachedRaw !== false) {
                $cachedJson = json_decode($cachedRaw, true);
                if (is_array($cachedJson)) {
                    return $cachedJson;
                }
            }
        }
    }

    $url = sprintf(
        '%s/minoristas/%d/locales/%d/promociones?estado=%s',
        $baseUrl,
        SCANNTECH_MINORISTA_FIXO,
        $filial,
        urlencode($estado)
    );

    $curl = curl_init($url);
    if ($curl === false) {
        throw new RuntimeException('Falha ao inicializar cliente HTTP.');
    }

    curl_setopt_array(
        $curl,
        [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPAUTH => CURLAUTH_BASIC,
            CURLOPT_USERPWD => $username . ':' . $password,
            CURLOPT_CONNECTTIMEOUT => max(3, min(10, $timeout)),
            CURLOPT_TIMEOUT => $timeout,
            CURLOPT_FAILONERROR => false,
            CURLOPT_HTTPHEADER => [
                'Accept: application/json',
            ],
        ]
    );

    $responseBody = curl_exec($curl);
    if ($responseBody === false) {
        $errorMessage = curl_error($curl);
        curl_close($curl);
        throw new RuntimeException('Erro de rede: ' . $errorMessage);
    }

    $statusCode = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);

    if ($statusCode >= 400) {
        $message = extract_error_message((string) $responseBody);
        throw new RuntimeException(
            sprintf('HTTP %d ao consultar filial %d. %s', $statusCode, $filial, $message),
            $statusCode
        );
    }

    $decoded = json_decode((string) $responseBody, true);
    if (!is_array($decoded)) {
        throw new RuntimeException('Resposta invalida da API para filial ' . $filial . '.');
    }

    if ($cacheTtl > 0) {
        if (!is_dir($cacheDir)) {
            mkdir($cacheDir, 0775, true);
        }
        file_put_contents($cacheFile, json_encode($decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }

    return $decoded;
}

/**
 * @param array<string, mixed> $payload
 * @return array<int, array<string, mixed>>
 */
function normalize_promocoes(array $payload, int $filial): array
{
    $results = $payload['results'] ?? [];
    if (!is_array($results)) {
        return [];
    }

    $normalized = [];
    foreach ($results as $promo) {
        if (!is_array($promo)) {
            continue;
        }

        $itens = extract_itens($promo);
        $formasPagamento = extract_formas_pagamento($promo);

        $binesMap = [];
        foreach ($formasPagamento as $forma) {
            foreach (($forma['bines'] ?? []) as $bin) {
                $trimmedBin = trim((string) $bin);
                if ($trimmedBin !== '') {
                    $binesMap[$trimmedBin] = $trimmedBin;
                }
            }
        }
        $bines = array_values($binesMap);

        $normalized[] = [
            'filial' => $filial,
            'id' => (int) ($promo['id'] ?? 0),
            'titulo' => (string) ($promo['titulo'] ?? ''),
            'descripcion' => (string) ($promo['descripcion'] ?? ''),
            'tipo' => (string) ($promo['tipo'] ?? ''),
            'autor' => (string) (($promo['autor']['descripcion'] ?? '') ?: ''),
            'vigenciaDesde' => (string) ($promo['vigenciaDesde'] ?? ''),
            'vigenciaHasta' => (string) ($promo['vigenciaHasta'] ?? ''),
            'limitePromocionesPorTicket' => $promo['limitePromocionesPorTicket'] ?? null,
            'itens' => $itens,
            'formasPagamento' => $formasPagamento,
            'bines' => $bines,
        ];
    }

    return $normalized;
}

/**
 * @param array<string, mixed> $promo
 * @return array<int, array<string, string>>
 */
function extract_itens(array $promo): array
{
    $items = $promo['detalles']['condiciones']['items'] ?? [];
    if (!is_array($items)) {
        return [];
    }

    $itensMap = [];
    foreach ($items as $item) {
        if (!is_array($item)) {
            continue;
        }

        $articulos = $item['articulos'] ?? [];
        if (!is_array($articulos)) {
            continue;
        }

        foreach ($articulos as $articulo) {
            if (!is_array($articulo)) {
                continue;
            }

            $nome = trim((string) ($articulo['nombre'] ?? ''));
            $codigoBarras = trim((string) ($articulo['codigoBarras'] ?? ''));
            if ($nome === '' && $codigoBarras === '') {
                continue;
            }

            $key = $codigoBarras . '|' . $nome;
            $itensMap[$key] = [
                'nombre' => $nome,
                'codigoBarras' => $codigoBarras,
            ];
        }
    }

    return array_values($itensMap);
}

/**
 * @param array<string, mixed> $promo
 * @return array<int, array<string, mixed>>
 */
function extract_formas_pagamento(array $promo): array
{
    $formas = $promo['detalles']['condiciones']['formasPago'] ?? [];
    if (!is_array($formas)) {
        return [];
    }

    $normalizadas = [];
    foreach ($formas as $forma) {
        if (!is_array($forma)) {
            continue;
        }

        $bines = parse_bines($forma['bines'] ?? []);
        $normalizadas[] = [
            'descripcion' => (string) ($forma['descripcion'] ?? ''),
            'codigoTipoPago' => $forma['codigoTipoPago'] ?? null,
            'codigoTarjeta' => $forma['codigoTarjeta'] ?? null,
            'codigoMoneda' => $forma['codigoMoneda'] ?? null,
            'bines' => $bines,
        ];
    }

    return $normalizadas;
}

/**
 * @return array<int, string>
 */
function parse_bines(mixed $raw): array
{
    $values = [];

    if (is_array($raw)) {
        foreach ($raw as $value) {
            $token = trim((string) $value);
            if ($token !== '') {
                $values[$token] = $token;
            }
        }
    } elseif (is_string($raw)) {
        $tokens = preg_split('/[\s,;]+/', $raw, -1, PREG_SPLIT_NO_EMPTY);
        if (is_array($tokens)) {
            foreach ($tokens as $token) {
                $trimmed = trim($token);
                if ($trimmed !== '') {
                    $values[$trimmed] = $trimmed;
                }
            }
        }
    }

    return array_values($values);
}

function extract_error_message(string $responseBody): string
{
    $clean = trim(strip_tags($responseBody));
    $clean = preg_replace('/\s+/', ' ', $clean) ?? $clean;
    if ($clean === '') {
        return 'Sem detalhes retornados.';
    }

    if (function_exists('mb_substr')) {
        return mb_substr($clean, 0, 240);
    }

    return substr($clean, 0, 240);
}
