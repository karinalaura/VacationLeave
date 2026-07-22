const form = document.getElementById('leave-form');
const errorMsg = document.getElementById('error-msg');
const resultEl = document.getElementById('result');
const breakdownToggle = document.getElementById('breakdown-toggle');
const breakdownTable = document.getElementById('breakdown-table');

const TIER_BREAKPOINT = 10;

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorMsg.classList.remove('visible');
  errorMsg.textContent = '';

  const payload = {
    start_date: document.getElementById('start_date').value,
    as_of_date: document.getElementById('as_of_date').value,
    leave_taken: document.getElementById('leave_taken').value || 0,
  };

  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!data.ok) {
      errorMsg.textContent = data.error;
      errorMsg.classList.add('visible');
      resultEl.classList.remove('visible');
      return;
    }

    renderResult(data.result);
  } catch (err) {
    errorMsg.textContent = 'Something went wrong reaching the server. Please try again.';
    errorMsg.classList.add('visible');
  }
});

function renderResult(result) {
  document.getElementById('years-of-service').textContent = `${result.years_of_service} yrs`;

  const tenureNote = document.getElementById('tenure-note');
  if (result.non_accruing_days > 0) {
    tenureNote.textContent = `(${result.calendar_years_of_service} yrs calendar tenure, minus ${result.non_accruing_days} non-accruing leave days)`;
    tenureNote.style.display = 'block';
  } else {
    tenureNote.style.display = 'none';
  }

  const tierBadge = document.getElementById('tier-badge');
  const isTier2 = result.full_years_completed >= TIER_BREAKPOINT;
  tierBadge.textContent = result.current_tier;
  tierBadge.classList.toggle('tier-2', isTier2);

  document.getElementById('accrued-value').textContent = `${result.accrued_leave} days`;
  document.getElementById('taken-value').textContent = `${result.leave_taken} days`;

  const balanceValue = document.getElementById('balance-value');
  balanceValue.textContent = `${result.balance} days`;
  balanceValue.classList.toggle('positive', result.balance >= 0);
  balanceValue.classList.toggle('negative', result.balance < 0);

  renderBreakdownTable(result.breakdown);

  resultEl.classList.add('visible');
}

function renderBreakdownTable(breakdown) {
  const tbody = breakdownTable.querySelector('tbody');
  tbody.innerHTML = '';

  breakdown.forEach((entry) => {
    const tr = document.createElement('tr');
    const statusLabel = entry.status === 'in_progress'
      ? `In progress (${entry.percent_complete}%)`
      : 'Complete';
    tr.innerHTML = `
      <td>Year ${entry.year_number}</td>
      <td>${entry.rate_per_year} days/yr</td>
      <td>${entry.days_earned} days</td>
      <td>${statusLabel}</td>
    `;
    tbody.appendChild(tr);
  });
}

breakdownToggle.addEventListener('click', () => {
  const isVisible = breakdownTable.classList.toggle('visible');
  breakdownToggle.textContent = isVisible ? 'Hide year-by-year breakdown' : 'Show year-by-year breakdown';
});
