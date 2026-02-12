<?php
declare(strict_types=1);

if (!function_exists('app_project_path')) {
    function app_project_path(string $relativePath = ''): string
    {
        $basePath = dirname(__DIR__);
        if ($relativePath === '') {
            return $basePath;
        }

        $normalized = str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $relativePath);
        return $basePath . DIRECTORY_SEPARATOR . ltrim($normalized, DIRECTORY_SEPARATOR);
    }
}

if (!function_exists('app_load_env_file')) {
    function app_load_env_file(string $filePath): void
    {
        if (!is_file($filePath)) {
            return;
        }

        $lines = file($filePath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if ($lines === false) {
            return;
        }

        foreach ($lines as $line) {
            $trimmed = trim($line);
            if ($trimmed === '' || str_starts_with($trimmed, '#')) {
                continue;
            }

            if (str_starts_with($trimmed, 'export ')) {
                $trimmed = trim(substr($trimmed, 7));
            }

            $separator = strpos($trimmed, '=');
            if ($separator === false) {
                continue;
            }

            $name = trim(substr($trimmed, 0, $separator));
            $value = trim(substr($trimmed, $separator + 1));
            if ($name === '') {
                continue;
            }

            if (
                (str_starts_with($value, '"') && str_ends_with($value, '"')) ||
                (str_starts_with($value, "'") && str_ends_with($value, "'"))
            ) {
                $value = substr($value, 1, -1);
            }

            putenv($name . '=' . $value);
            $_ENV[$name] = $value;
            $_SERVER[$name] = $value;
        }
    }
}

app_load_env_file(app_project_path('.env'));
app_load_env_file(app_project_path('config/.env'));

if (!function_exists('app_env')) {
    function app_env(string $key, ?string $default = null): ?string
    {
        $value = $_ENV[$key] ?? $_SERVER[$key] ?? getenv($key);
        if ($value === false || $value === null || $value === '') {
            return $default;
        }

        return (string) $value;
    }
}

if (!function_exists('app_json_response')) {
    function app_json_response(array $payload, int $statusCode = 200): void
    {
        http_response_code($statusCode);
        header('Content-Type: application/json; charset=utf-8');

        $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json === false) {
            echo '{"error":"Falha ao serializar JSON"}';
            return;
        }

        echo $json;
    }
}

if (!function_exists('app_normalize_int_list')) {
    function app_normalize_int_list(array $values): array
    {
        $normalized = [];
        foreach ($values as $value) {
            if (is_string($value)) {
                $value = trim($value);
                if ($value === '') {
                    continue;
                }
            }

            if (!is_numeric($value)) {
                continue;
            }

            $number = (int) $value;
            if ($number > 0) {
                $normalized[$number] = $number;
            }
        }

        ksort($normalized, SORT_NUMERIC);
        return array_values($normalized);
    }
}

if (!function_exists('app_read_filiais')) {
    function app_read_filiais(string $filePath): array
    {
        if (!is_file($filePath)) {
            return [];
        }

        $raw = file_get_contents($filePath);
        if ($raw === false) {
            return [];
        }

        $decoded = json_decode($raw, true);
        if (!is_array($decoded)) {
            return [];
        }

        $filiais = $decoded['filiais'] ?? [];
        if (!is_array($filiais)) {
            return [];
        }

        return app_normalize_int_list($filiais);
    }
}

if (!function_exists('app_write_filiais')) {
    function app_write_filiais(string $filePath, array $filiais): bool
    {
        $directory = dirname($filePath);
        if (!is_dir($directory)) {
            mkdir($directory, 0775, true);
        }

        $payload = [
            'filiais' => app_normalize_int_list($filiais),
        ];

        $json = json_encode(
            $payload,
            JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
        );

        if ($json === false) {
            return false;
        }

        return file_put_contents($filePath, $json . PHP_EOL, LOCK_EX) !== false;
    }
}
