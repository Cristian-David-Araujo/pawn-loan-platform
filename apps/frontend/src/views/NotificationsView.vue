<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()
const error = ref('')

const form = reactive({
  channel: 'email',
  recipient: '',
  message: '',
})

function send() {
  error.value = ''
  if (!form.recipient || !form.message) {
    error.value = 'Recipient and message are required'
    return
  }
  store.sendNotification(form)
  form.recipient = ''
  form.message = ''
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Send Notification</h3>
      <div class="form-grid">
        <select v-model="form.channel">
          <option value="email">Email</option>
          <option value="sms">SMS</option>
          <option value="whatsapp">WhatsApp</option>
        </select>
        <input v-model="form.recipient" placeholder="Recipient" />
        <input v-model="form.message" placeholder="Message" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="send">Send</button>
    </article>

    <article class="card">
      <h3>Notification History</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Channel</th>
              <th>Recipient</th>
              <th>Message</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in store.notifications" :key="n.id">
              <td>{{ n.id }}</td>
              <td>{{ n.channel }}</td>
              <td>{{ n.recipient }}</td>
              <td>{{ n.message }}</td>
              <td>{{ n.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>
