<template>
  <div class="flex h-screen">
    <aside class="w-64 bg-gray-900 text-white p-4">
      <h2 class="text-lg font-bold mb-4">Admin</h2>
      <nav class="space-y-2">
        <router-link to="/admin/dashboard" class="block px-3 py-2 rounded hover:bg-gray-700">Dashboard</router-link>
        <router-link to="/admin/knowledge-bases" class="block px-3 py-2 rounded hover:bg-gray-700">Knowledge Bases</router-link>
        <router-link to="/admin/documents" class="block px-3 py-2 rounded hover:bg-gray-700">Documents</router-link>
        <router-link to="/admin/rag-config" class="block px-3 py-2 rounded hover:bg-gray-700">RAG Config</router-link>
        <router-link to="/admin/models" class="block px-3 py-2 rounded hover:bg-gray-700">Models</router-link>
        <router-link to="/admin/qa-logs" class="block px-3 py-2 rounded hover:bg-gray-700">QA Logs</router-link>
      </nav>
    </aside>
    <main class="flex-1 p-6 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
