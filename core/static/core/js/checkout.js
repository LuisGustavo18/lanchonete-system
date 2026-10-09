(() => {
  'use strict';

  const form = document.querySelector('[data-checkout-form]');
  if (!form) return;

  const orderType = document.getElementById('checkout-order_type');
  const address = document.getElementById('delivery-address');
  const addressRequired = ['street', 'number', 'neighborhood', 'city', 'state', 'zip_code'];
  const payment = document.getElementById('checkout-payment_method');
  const cashChange = document.getElementById('cash-change-field');
  const paymentHelp = document.getElementById('checkout-payment-help');
  const totalDisplay = document.getElementById('checkout-total');
  const submitTotal = document.getElementById('checkout-submit-total');
  const deliveryFeeLine = document.getElementById('delivery-fee-line');
  const cashAmount = document.getElementById('checkout-cash_change_for');
  const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const remember = document.getElementById('remember-checkout');
  const forget = document.getElementById('forget-checkout');
  const status = document.getElementById('remember-checkout-status');
  const storageKey = `lanchonete:checkout:${form.dataset.businessId}:v1`;
  const lifetime = 90 * 24 * 60 * 60 * 1000;
  // Keep an explicit allowlist: order, payment, token and card data never belong here.
  const savedFields = {
    name: 150, phone: 20, street: 150, number: 20, neighborhood: 100,
    city: 100, state: 2, zip_code: 9, complement: 100, reference: 150,
  };
  let storageAvailable = true;

  function storageUnavailable() {
    storageAvailable = false;
    remember.checked = false;
    remember.disabled = true;
    forget.classList.add('hidden');
    status.textContent = 'Este navegador não permitiu salvar os dados. Você pode finalizar seu pedido normalmente.';
  }

  function deleteSaved(message) {
    try {
      window.localStorage.removeItem(storageKey);
      forget.classList.add('hidden');
      status.textContent = message;
    } catch (_) {
      storageUnavailable();
    }
  }

  function updateAddress() {
    const delivery = orderType.value === 'DELIVERY';
    address.hidden = !delivery;
    address.disabled = !delivery;
    addressRequired.forEach(name => {
      document.getElementById(`checkout-${name}`).required = delivery;
    });
    deliveryFeeLine.hidden = !delivery;
    const subtotal = Math.round(Number(totalDisplay.dataset.subtotal) * 100);
    const fee = delivery ? Math.round(Number(totalDisplay.dataset.deliveryFee) * 100) : 0;
    const total = (subtotal + fee) / 100;
    totalDisplay.textContent = currency.format(total);
    if (submitTotal) submitTotal.textContent = currency.format(total);
    if (cashAmount) cashAmount.min = total.toFixed(2);
  }

  function updatePayment() {
    const cash = payment.value === 'DINHEIRO';
    cashChange.hidden = !cash;
    cashChange.disabled = !cash;
    if (payment.value === 'PIX') {
      paymentHelp.textContent = 'Após enviar o pedido, use a chave Pix da loja exibida na confirmação. A equipe confirma o recebimento do pagamento.';
    } else if (cash) {
      paymentHelp.textContent = 'Pague em dinheiro na entrega ou na retirada. Informe abaixo se precisar de troco.';
    } else {
      paymentHelp.textContent = 'Pague com cartão na maquininha, na entrega ou na retirada.';
    }
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (raw) {
      let saved;
      try { saved = JSON.parse(raw); } catch (_) { saved = null; }
      const age = saved ? Date.now() - saved.savedAt : NaN;
      const valid = saved && saved.version === 1 && typeof saved.savedAt === 'number'
        && Number.isFinite(age) && age >= 0 && age < lifetime
        && saved.fields && typeof saved.fields === 'object' && !Array.isArray(saved.fields);
      if (!valid) {
        deleteSaved('Os dados antigos foram apagados. Marque a opção para lembrar os novos dados.');
      } else {
        forget.classList.remove('hidden');
        if (form.dataset.isBound !== 'true') {
          remember.checked = true;
          Object.entries(savedFields).forEach(([name, limit]) => {
            const field = document.getElementById(`checkout-${name}`);
            if (field && !field.value && typeof saved.fields[name] === 'string') {
              field.value = saved.fields[name].slice(0, limit);
            }
          });
          status.textContent = 'Dados preenchidos deste dispositivo. Confira antes de enviar.';
        }
      }
    }
  } catch (_) {
    storageUnavailable();
  }

  remember.addEventListener('change', () => {
    if (!remember.checked) {
      deleteSaved('Dados salvos apagados. Seus dados continuam neste formulário, mas não serão lembrados no próximo pedido.');
    } else {
      status.textContent = 'Seus dados serão lembrados ao enviar este pedido.';
    }
  });

  forget.addEventListener('click', () => {
    remember.checked = false;
    deleteSaved('Dados salvos apagados. Seus dados continuam neste formulário, mas não serão lembrados no próximo pedido.');
    remember.focus();
  });

  form.addEventListener('submit', () => {
    if (!storageAvailable || !form.checkValidity()) return;
    if (!remember.checked) {
      deleteSaved('');
      return;
    }
    const fields = {};
    Object.entries(savedFields).forEach(([name, limit]) => {
      const field = document.getElementById(`checkout-${name}`);
      fields[name] = field ? field.value.trim().slice(0, limit) : '';
    });
    try {
      window.localStorage.setItem(storageKey, JSON.stringify({ version: 1, savedAt: Date.now(), fields }));
    } catch (_) {
      storageUnavailable();
    }
  });

  orderType.addEventListener('change', updateAddress);
  payment.addEventListener('change', updatePayment);
  updateAddress();
  updatePayment();
})();
