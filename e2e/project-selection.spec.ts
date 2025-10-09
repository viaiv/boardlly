import { test, expect } from '@playwright/test';

/**
 * Testes E2E para verificar o problema:
 * "Após login, o app mostra 'Nenhum projeto', mas tenho projetos cadastrados"
 */

test.describe('Project Selection Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Limpar localStorage para começar do zero
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('deve mostrar "Nenhum projeto" quando não há projetos cadastrados', async ({ page }) => {
    // Registrar novo usuário
    await page.goto('/register');
    await page.fill('input[type="email"]', `test${Date.now()}@example.com`);
    await page.fill('input[type="password"]', 'supersecret123');
    await page.fill('input[name="name"]', 'Test User');
    await page.click('button[type="submit"]');

    // Aguardar redirecionamento para tela de seleção de projeto
    await page.waitForURL('/project-selection', { timeout: 10000 });

    // Verificar se a mensagem de "Nenhum projeto" aparece
    await expect(page.locator('text=Nenhum projeto conectado')).toBeVisible();
  });

  test('deve listar projetos quando há projetos cadastrados', async ({ page, request }) => {
    // 1. Registrar usuário e criar conta
    await page.goto('/register');
    const email = `test${Date.now()}@example.com`;
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'supersecret123');
    await page.fill('input[name="name"]', 'Test User');
    await page.click('button[type="submit"]');

    // 2. Fazer login para obter sessão
    await page.goto('/login');
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'supersecret123');
    await page.click('button[type="submit"]');

    // 3. Criar conta via API (usando a sessão do browser)
    const apiContext = page.context();
    const accountResponse = await apiContext.request.post('http://localhost:8000/api/accounts', {
      data: { name: 'Test Account' },
    });
    expect(accountResponse.ok()).toBeTruthy();

    // 4. Criar projeto via API direta (simulando projeto já existente no banco)
    // Nota: Precisaríamos inserir direto no banco ou ter um endpoint de seed
    // Por enquanto, vamos apenas verificar que a API /api/projects retorna algo

    // 5. Recarregar página para forçar nova busca de projetos
    await page.reload();

    // 6. Verificar se projetos são listados
    const projectsResponse = await apiContext.request.get('http://localhost:8000/api/projects');
    const projects = await projectsResponse.json();
    console.log('Projetos retornados pela API:', projects);

    // Se não houver projetos, deveria mostrar "Nenhum projeto"
    if (projects.length === 0) {
      await expect(page.locator('text=Nenhum projeto conectado')).toBeVisible();
    } else {
      // Se houver projetos, deveria listar
      await expect(page.locator('text=Selecione um Projeto')).toBeVisible();
    }
  });

  test('REPRODUZIR BUG: localStorage com projeto inexistente', async ({ page }) => {
    /**
     * Este teste reproduz o cenário específico relatado:
     * - localStorage tem um activeProjectId
     * - Mas /api/projects retorna array vazio
     * - /roadmap funciona (porque usa o ID do localStorage)
     * - Mas tela inicial mostra "Nenhum projeto"
     */

    // 1. Criar usuário e fazer login
    await page.goto('/register');
    const email = `test${Date.now()}@example.com`;
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'supersecret123');
    await page.fill('input[name="name"]', 'Test User');
    await page.click('button[type="submit"]');

    // 2. Fazer login
    await page.goto('/login');
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'supersecret123');
    await page.click('button[type="submit"]');

    // 3. Criar conta
    const apiContext = page.context();
    await apiContext.request.post('http://localhost:8000/api/accounts', {
      data: { name: 'Test Account' },
    });

    // 4. SIMULAR O BUG: Definir um activeProjectId no localStorage que não existe
    await page.evaluate(() => {
      localStorage.setItem('tactyo:active-project-id', '999');
    });

    // 5. Navegar para a página inicial (que deve redirecionar para /project-selection)
    await page.goto('/');

    // 6. Verificar comportamento atual
    // Deveria mostrar "Nenhum projeto" porque /api/projects retorna []
    await expect(page.locator('text=Nenhum projeto conectado')).toBeVisible({ timeout: 5000 });

    // 7. Tentar acessar /roadmap (que deveria funcionar SE o projeto 999 existisse)
    await page.goto('/roadmap');

    // Verificar se há erro ao carregar roadmap
    // Se o projeto não existir, deve mostrar erro
    const errorMessage = page.locator('text=Projeto não encontrado');
    const loadingMessage = page.locator('text=Carregando roadmap');
    const noProjectMessage = page.locator('text=Nenhum Project conectado');

    // Aguardar um dos elementos aparecer
    await Promise.race([
      errorMessage.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
      noProjectMessage.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
      loadingMessage.waitFor({ state: 'visible', timeout: 1000 }).catch(() => null),
    ]);

    // Registrar estado para debug
    const pageContent = await page.content();
    console.log('Estado da página /roadmap:', {
      hasError: await errorMessage.isVisible().catch(() => false),
      hasNoProject: await noProjectMessage.isVisible().catch(() => false),
      hasLoading: await loadingMessage.isVisible().catch(() => false),
    });
  });

  test('CENÁRIO REAL: Verificar estado atual do banco', async ({ page, request }) => {
    /**
     * Este teste verifica o estado real do banco de dados:
     * - Faz login com credenciais existentes
     * - Verifica quantos projetos estão cadastrados
     * - Verifica se o localStorage tem activeProjectId
     * - Compara com o que a API retorna
     */

    // Nota: Precisamos de credenciais reais para este teste
    // Ajustar conforme necessário
    await page.goto('/login');

    // Se você tiver um usuário de teste, usar aqui
    // Caso contrário, este teste pode ser ignorado
    const hasLoginForm = await page.locator('input[type="email"]').isVisible().catch(() => false);

    if (!hasLoginForm) {
      test.skip(true, 'Teste requer credenciais de usuário real');
      return;
    }

    // TODO: Adicionar credenciais de teste reais aqui
    // await page.fill('input[type="email"]', 'seu-email@exemplo.com');
    // await page.fill('input[type="password"]', 'sua-senha');
    // await page.click('button[type="submit"]');

    test.skip(true, 'Configure credenciais reais para testar cenário atual');
  });
});
