<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/config/bootstrap.php';

session_name('scanntech_admin');
session_start();

$sessionKey = 'admin_filiais_authenticated';
if (!isset($_SESSION[$sessionKey])) {
    $_SESSION[$sessionKey] = false;
}

$adminPassword = trim((string) app_env('ADMIN_FILIAIS_PASSWORD', ''));
$isPasswordConfigured = $adminPassword !== '';

$notice = '';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $authAction = strtolower(trim((string) ($_POST['auth_action'] ?? '')));

    if ($authAction === 'logout') {
        $_SESSION[$sessionKey] = false;
        header('Location: filiais.php');
        exit;
    }

    if ($authAction === 'login') {
        $submittedPassword = (string) ($_POST['admin_password'] ?? '');
        if (!$isPasswordConfigured) {
            $error = 'Configure ADMIN_FILIAIS_PASSWORD em config/.env.';
        } elseif (hash_equals($adminPassword, $submittedPassword)) {
            $_SESSION[$sessionKey] = true;
            header('Location: filiais.php');
            exit;
        } else {
            $error = 'Senha invalida.';
        }
    }
}

$isAuthenticated = $isPasswordConfigured && ($_SESSION[$sessionKey] === true);

if (!$isAuthenticated) {
    ?>
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Acesso Administracao de Filiais</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: linear-gradient(160deg, #0f172a 0%, #111827 55%, #1e293b 100%);
                color: #e2e8f0;
                min-height: 100vh;
            }
        </style>
    </head>
    <body class="px-4 py-6 md:px-8">
        <main class="mx-auto max-w-xl rounded-2xl border border-slate-700 bg-slate-900/70 p-5 shadow-2xl">
            <h1 class="mb-2 text-2xl font-bold text-white">Administracao de Filiais</h1>
            <p class="mb-4 text-sm text-slate-300">Acesso protegido por senha.</p>

            <?php if ($error !== ''): ?>
                <div class="mb-4 rounded-lg border border-rose-400/60 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
                    <?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?>
                </div>
            <?php endif; ?>

            <?php if (!$isPasswordConfigured): ?>
                <div class="mb-4 rounded-lg border border-amber-400/60 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                    Defina <code>ADMIN_FILIAIS_PASSWORD</code> no arquivo <code>config/.env</code> para liberar o acesso.
                </div>
            <?php else: ?>
                <form method="post" class="grid gap-3">
                    <input type="hidden" name="auth_action" value="login">
                    <label class="grid gap-1 text-sm">
                        <span class="text-slate-300">Senha</span>
                        <input
                            name="admin_password"
                            type="password"
                            required
                            class="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                        >
                    </label>
                    <button type="submit" class="rounded-lg border border-cyan-400/60 bg-cyan-500/20 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-500/30">
                        Entrar
                    </button>
                </form>
            <?php endif; ?>

            <a href="../index.php" class="mt-4 inline-flex rounded-lg border border-slate-500/60 bg-slate-700/30 px-4 py-2 text-sm font-semibold text-slate-100 hover:bg-slate-700/40">
                Voltar para consulta
            </a>
        </main>
    </body>
    </html>
    <?php
    exit;
}

$filiaisPath = app_project_path('storage/filiais.json');
$filiais = app_read_filiais($filiaisPath);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = strtolower(trim((string) ($_POST['action'] ?? '')));
    $working = $filiais;

    if ($action === 'add') {
        $newFilial = (int) ($_POST['filial'] ?? 0);
        if ($newFilial <= 0) {
            $error = 'Informe uma filial valida.';
        } elseif (in_array($newFilial, $working, true)) {
            $error = 'A filial ja existe.';
        } else {
            $working[] = $newFilial;
            $notice = 'Filial incluida com sucesso.';
        }
    } elseif ($action === 'update') {
        $oldFilial = (int) ($_POST['old_filial'] ?? 0);
        $newFilial = (int) ($_POST['new_filial'] ?? 0);

        if ($oldFilial <= 0 || $newFilial <= 0) {
            $error = 'Valores de filial invalidos.';
        } elseif (!in_array($oldFilial, $working, true)) {
            $error = 'Filial original nao encontrada.';
        } elseif ($newFilial !== $oldFilial && in_array($newFilial, $working, true)) {
            $error = 'A nova filial informada ja existe.';
        } else {
            $working = array_values(array_filter($working, static fn (int $id): bool => $id !== $oldFilial));
            $working[] = $newFilial;
            $notice = 'Filial atualizada com sucesso.';
        }
    } elseif ($action === 'delete') {
        $deleteFilial = (int) ($_POST['filial'] ?? 0);
        if ($deleteFilial <= 0) {
            $error = 'Filial invalida para remocao.';
        } elseif (!in_array($deleteFilial, $working, true)) {
            $error = 'Filial nao encontrada para remocao.';
        } else {
            $working = array_values(array_filter($working, static fn (int $id): bool => $id !== $deleteFilial));
            $notice = 'Filial removida com sucesso.';
        }
    } elseif ($action !== '') {
        $error = 'Acao invalida.';
    }

    if ($error === '' && $action !== '') {
        if (!app_write_filiais($filiaisPath, $working)) {
            $error = 'Falha ao salvar arquivo de filiais.';
        } else {
            $redirect = 'filiais.php?msg=' . urlencode($notice);
            header('Location: ' . $redirect);
            exit;
        }
    }
}

if (isset($_GET['msg']) && $_GET['msg'] !== '') {
    $notice = (string) $_GET['msg'];
}

$filiais = app_read_filiais($filiaisPath);
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Administracao de Filiais</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(160deg, #0f172a 0%, #111827 55%, #1e293b 100%);
            color: #e2e8f0;
            min-height: 100vh;
        }
    </style>
</head>
<body class="px-4 py-6 md:px-8">
    <main class="mx-auto max-w-5xl rounded-2xl border border-slate-700 bg-slate-900/70 p-5 shadow-2xl">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
                <h1 class="text-2xl font-bold text-white">Administrar Filiais</h1>
                <p class="text-sm text-slate-300">Arquivo fonte: <code>storage/filiais.json</code></p>
            </div>
            <div class="flex items-center gap-2">
                <form method="post">
                    <input type="hidden" name="auth_action" value="logout">
                    <button type="submit" class="rounded-lg border border-rose-400/60 bg-rose-500/15 px-4 py-2 text-sm font-semibold text-rose-100 hover:bg-rose-500/25">
                        Sair
                    </button>
                </form>
                <a href="../index.php" class="rounded-lg border border-slate-500/60 bg-slate-700/30 px-4 py-2 text-sm font-semibold text-slate-100 hover:bg-slate-700/40">
                    Voltar para consulta
                </a>
            </div>
        </div>

        <?php if ($notice !== ''): ?>
            <div class="mb-4 rounded-lg border border-emerald-400/60 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
                <?= htmlspecialchars($notice, ENT_QUOTES, 'UTF-8') ?>
            </div>
        <?php endif; ?>

        <?php if ($error !== ''): ?>
            <div class="mb-4 rounded-lg border border-rose-400/60 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
                <?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?>
            </div>
        <?php endif; ?>

        <section class="mb-6 rounded-xl border border-slate-700 bg-slate-950/40 p-4">
            <h2 class="mb-3 text-lg font-semibold text-white">Incluir nova filial</h2>
            <form method="post" class="flex flex-wrap items-end gap-3">
                <input type="hidden" name="action" value="add">
                <label class="grid gap-1 text-sm">
                    <span class="text-slate-300">Codigo da filial</span>
                    <input
                        name="filial"
                        type="number"
                        min="1"
                        step="1"
                        required
                        class="w-48 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                        placeholder="Ex: 53"
                    >
                </label>
                <button type="submit" class="rounded-lg border border-cyan-400/60 bg-cyan-500/20 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-500/30">
                    Incluir filial
                </button>
            </form>
        </section>

        <section class="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
            <h2 class="mb-3 text-lg font-semibold text-white">Filiais cadastradas</h2>
            <?php if ($filiais === []): ?>
                <p class="text-sm text-slate-400">Nenhuma filial cadastrada.</p>
            <?php else: ?>
                <div class="overflow-auto rounded-lg border border-slate-700">
                    <table class="min-w-full divide-y divide-slate-700 text-sm">
                        <thead class="bg-slate-800/70 text-left text-xs uppercase tracking-wide text-slate-300">
                            <tr>
                                <th class="px-3 py-3">Filial atual</th>
                                <th class="px-3 py-3">Editar</th>
                                <th class="px-3 py-3">Excluir</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            <?php foreach ($filiais as $filial): ?>
                                <tr class="hover:bg-slate-800/40">
                                    <td class="px-3 py-3 font-semibold text-white"><?= htmlspecialchars((string) $filial, ENT_QUOTES, 'UTF-8') ?></td>
                                    <td class="px-3 py-3">
                                        <form method="post" class="flex flex-wrap items-center gap-2">
                                            <input type="hidden" name="action" value="update">
                                            <input type="hidden" name="old_filial" value="<?= htmlspecialchars((string) $filial, ENT_QUOTES, 'UTF-8') ?>">
                                            <input
                                                name="new_filial"
                                                type="number"
                                                min="1"
                                                step="1"
                                                required
                                                value="<?= htmlspecialchars((string) $filial, ENT_QUOTES, 'UTF-8') ?>"
                                                class="w-24 rounded-md border border-slate-600 bg-slate-900 px-2 py-1 text-slate-100 outline-none focus:border-cyan-400"
                                            >
                                            <button type="submit" class="rounded-md border border-indigo-400/60 bg-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-100 hover:bg-indigo-500/30">
                                                Salvar
                                            </button>
                                        </form>
                                    </td>
                                    <td class="px-3 py-3">
                                        <form method="post" onsubmit="return confirm('Deseja remover a filial <?= htmlspecialchars((string) $filial, ENT_QUOTES, 'UTF-8') ?>?')">
                                            <input type="hidden" name="action" value="delete">
                                            <input type="hidden" name="filial" value="<?= htmlspecialchars((string) $filial, ENT_QUOTES, 'UTF-8') ?>">
                                            <button type="submit" class="rounded-md border border-rose-400/60 bg-rose-500/20 px-3 py-1 text-xs font-semibold text-rose-100 hover:bg-rose-500/30">
                                                Excluir
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            <?php endif; ?>
        </section>
    </main>
</body>
</html>
