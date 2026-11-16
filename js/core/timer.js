// Cronômetro por pergunta.
//
// Em vez de apenas "subtrair 1 a cada segundo" (o que atrasa quando o navegador
// está ocupado), guardamos o MOMENTO em que o tempo acaba (deadline) e, a cada
// verificação, calculamos quanto falta. Assim a contagem nunca "escorrega".
//
// A interface (Etapa 4) só precisa de: start(), stop(), getRemaining().
// O 4º parâmetro (scheduler) existe para os testes automáticos poderem
// "avançar o relógio" sem esperar 30 segundos de verdade.

const CHECK_INTERVAL_MS = 250; // verifica 4x por segundo para a contagem ficar precisa

const defaultScheduler = {
  now: () => (globalThis.performance ? globalThis.performance.now() : Date.now()),
  setInterval: (callback, ms) => globalThis.setInterval(callback, ms),
  clearInterval: id => globalThis.clearInterval(id)
};

export function createQuestionTimer(seconds, onExpire, onTick = () => {}, scheduler = defaultScheduler) {
  const totalMs = seconds * 1000;
  let remainingWhenPaused = totalMs; // quanto faltava quando o cronômetro parou
  let deadline = null;               // instante em que o tempo acaba (só enquanto roda)
  let intervalId = null;
  let lastShown = null;              // último valor (em segundos) enviado para onTick
  let expired = false;

  function remainingMs() {
    if (deadline === null) return remainingWhenPaused;
    return Math.max(0, deadline - scheduler.now());
  }

  function remainingSeconds() {
    return Math.ceil(remainingMs() / 1000);
  }

  function clearTicker() {
    if (intervalId !== null) scheduler.clearInterval(intervalId);
    intervalId = null;
  }

  function check() {
    const secondsLeft = remainingSeconds();
    // Só avisa a interface quando o número mostrado realmente muda.
    if (secondsLeft !== lastShown) {
      lastShown = secondsLeft;
      onTick(secondsLeft);
    }
    if (secondsLeft <= 0 && !expired) {
      expired = true;
      clearTicker();
      remainingWhenPaused = 0;
      deadline = null;
      onExpire(); // chamado uma única vez
    }
  }

  return {
    start() {
      if (intervalId !== null || expired) return;
      deadline = scheduler.now() + remainingWhenPaused;
      intervalId = scheduler.setInterval(check, CHECK_INTERVAL_MS);
      check(); // mostra o valor inicial imediatamente (ex.: 30)
    },
    stop() {
      if (deadline !== null) remainingWhenPaused = remainingMs(); // congela o tempo restante
      deadline = null;
      clearTicker();
    },
    getRemaining() {
      return remainingSeconds();
    },
    getElapsedMs() {
      return totalMs - remainingMs();
    },
    isExpired() {
      return expired || remainingMs() <= 0;
    },
    isRunning() {
      return intervalId !== null;
    }
  };
}
