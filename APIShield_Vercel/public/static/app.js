// Presentation only. Authentication and authorization always run on the server.
document.querySelectorAll('.simulation-form').forEach((form) => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button');
    button.disabled = true;
    button.textContent = 'Running actual HTTP requests…';
    button.setAttribute('aria-busy', 'true');
  });
});
