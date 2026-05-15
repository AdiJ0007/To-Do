const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const state = {
  token: localStorage.getItem("todo_access_token") || "",
  currentUser: null,
  authMode: "login",
  users: [],
  projects: [],
  todos: [],
  stats: { total: 0, completed: 0, pending: 0, high_priority: 0 },
  filters: {
    search: "",
    status: "all",
    priority: "all",
    projectId: "all",
    sortBy: "created_at",
    sortOrder: "desc",
  },
  editingTodoId: null,
  editingTodo: null,
  editingProjectId: null,
};

const els = {
  sessionName: document.getElementById("sessionName"),
  sessionChip: document.getElementById("sessionChip"),
  signOutBtn: document.getElementById("signOutBtn"),
  authView: document.getElementById("authView"),
  workspaceView: document.getElementById("workspaceView"),
  authForm: document.getElementById("authForm"),
  authName: document.getElementById("authName"),
  authEmail: document.getElementById("authEmail"),
  authPassword: document.getElementById("authPassword"),
  authSubmitBtn: document.getElementById("authSubmitBtn"),
  googleSignInBtn: document.getElementById("googleSignInBtn"),
  loginTabBtn: document.getElementById("loginTabBtn"),
  registerTabBtn: document.getElementById("registerTabBtn"),
  nameField: document.getElementById("nameField"),
  projectForm: document.getElementById("projectForm"),
  projectName: document.getElementById("projectName"),
  projectDescription: document.getElementById("projectDescription"),
  projectMemberIds: document.getElementById("projectMemberIds"),
  projectList: document.getElementById("projectList"),
  projectSelect: document.getElementById("projectSelect"),
  projectFilter: document.getElementById("projectFilter"),
  todoForm: document.getElementById("todoForm"),
  todoList: document.getElementById("todoList"),
  template: document.getElementById("todoItemTemplate"),
  projectTemplate: document.getElementById("projectItemTemplate"),
  projectDialog: document.getElementById("projectDialog"),
  projectEditForm: document.getElementById("projectEditForm"),
  cancelProjectEditBtn: document.getElementById("cancelProjectEditBtn"),
  editProjectName: document.getElementById("editProjectName"),
  editProjectDescription: document.getElementById("editProjectDescription"),
  editProjectCurrentMembers: document.getElementById("editProjectCurrentMembers"),
  editProjectMemberIds: document.getElementById("editProjectMemberIds"),
  manageUsersBtn: document.getElementById("manageUsersBtn"),
  usersDialog: document.getElementById("usersDialog"),
  usersList: document.getElementById("usersList"),
  closeUsersBtn: document.getElementById("closeUsersBtn"),
  statTotal: document.getElementById("statTotal"),
  statCompleted: document.getElementById("statCompleted"),
  statPending: document.getElementById("statPending"),
  statHighPriority: document.getElementById("statHighPriority"),
  searchInput: document.getElementById("searchInput"),
  statusFilter: document.getElementById("statusFilter"),
  priorityFilter: document.getElementById("priorityFilter"),
  sortBy: document.getElementById("sortBy"),
  sortOrder: document.getElementById("sortOrder"),
  refreshBtn: document.getElementById("refreshBtn"),
  feedback: document.getElementById("feedback"),
  editDialog: document.getElementById("editDialog"),
  editForm: document.getElementById("editForm"),
  cancelEditBtn: document.getElementById("cancelEditBtn"),
  editTitle: document.getElementById("editTitle"),
  editDescription: document.getElementById("editDescription"),
  editPriority: document.getElementById("editPriority"),
  editDueDate: document.getElementById("editDueDate"),
  editProjectId: document.getElementById("editProjectId"),
  editAssigneeIds: document.getElementById("editAssigneeIds"),
  title: document.getElementById("title"),
  description: document.getElementById("description"),
  priority: document.getElementById("priority"),
  dueDate: document.getElementById("dueDate"),
  todoAssigneeIds: document.getElementById("todoAssigneeIds"),
};

function setFeedback(message, isError = false) {
  els.feedback.textContent = message;
  els.feedback.style.color = isError ? "#b33131" : "#5b6270";
}

function getUserDisplayName(userId) {
  if (!userId) {
    return "Unknown user";
  }
  const user = state.users.find((entry) => entry.id === userId);
  return user ? user.name : `User ${userId}`;
}

function getProjectDisplayName(projectId) {
  if (!projectId) {
    return "No project";
  }
  const project = state.projects.find((entry) => entry.id === projectId);
  return project ? project.name : `Project ${projectId}`;
}

function formatDate(dateString) {
  if (!dateString) {
    return "No due date";
  }
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return "Invalid date";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function toLocalDateTimeInputValue(isoDate) {
  if (!isoDate) {
    return "";
  }
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromInputDateToIso(value) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

function selectedValues(selectElement) {
  return Array.from(selectElement.selectedOptions).map((option) => Number(option.value)).filter(Number.isFinite);
}

function setSelectOptions(selectElement, items, { includeEmpty = false, emptyLabel = "All" } = {}) {
  const currentValue = selectElement.value;
  selectElement.innerHTML = "";

  if (includeEmpty) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = emptyLabel;
    selectElement.append(option);
  }

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.value);
    option.textContent = item.label;
    if (item.selected) {
      option.selected = true;
    }
    selectElement.append(option);
  });

  if (!includeEmpty && currentValue) {
    selectElement.value = currentValue;
  }
}

function setMultiSelectOptions(selectElement, items, selectedValues = []) {
  selectElement.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.value);
    option.textContent = item.label;
    option.selected = selectedValues.includes(item.value);
    selectElement.append(option);
  });
}

function renderChipList(container, items, { className, getLabel, onRemove }) {
  container.innerHTML = "";

  items.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = className;

    const label = document.createElement("span");
    label.textContent = getLabel(item);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "×";
    removeButton.addEventListener("click", () => onRemove(item));

    chip.append(label, removeButton);
    container.append(chip);
  });
}

function parseOAuthReturn() {
  const hash = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
  if (!hash) {
    return null;
  }

  const params = new URLSearchParams(hash);
  const accessToken = params.get("access_token");
  const userText = params.get("user");
  if (!accessToken || !userText) {
    return null;
  }

  try {
    return {
      accessToken,
      user: JSON.parse(userText),
    };
  } catch {
    return null;
  }
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isRegister = mode === "register";
  els.loginTabBtn.classList.toggle("active", !isRegister);
  els.registerTabBtn.classList.toggle("active", isRegister);
  els.nameField.style.display = isRegister ? "block" : "none";
  els.authName.required = isRegister;
  els.authName.disabled = !isRegister;
  els.authSubmitBtn.textContent = isRegister ? "Register" : "Sign In";
}

function showWorkspace() {
  els.authView.classList.add("hidden");
  els.workspaceView.classList.remove("hidden");
  els.sessionChip.classList.remove("hidden");
  document.querySelector(".topbar-actions .nav-link")?.classList.remove("hidden");
  // Show manage users button only for admins
  if (state.currentUser?.role === "admin") {
    els.manageUsersBtn?.classList.remove("hidden");
  } else {
    els.manageUsersBtn?.classList.add("hidden");
  }
}

function showAuth() {
  els.workspaceView.classList.add("hidden");
  els.authView.classList.remove("hidden");
  els.sessionChip.classList.add("hidden");
  document.querySelector(".topbar-actions .nav-link")?.classList.add("hidden");
  els.manageUsersBtn?.classList.add("hidden");
}

function setSession(token, user) {
  state.token = token;
  state.currentUser = user;
  localStorage.setItem("todo_access_token", token);
  localStorage.setItem("todo_current_user", JSON.stringify(user));
  els.sessionName.textContent = `${user.name} · ${user.email}`;
  showWorkspace();
}

function clearSession(message = "") {
  state.token = "";
  state.currentUser = null;
  state.users = [];
  state.projects = [];
  state.todos = [];
  state.stats = { total: 0, completed: 0, pending: 0, high_priority: 0 };
  localStorage.removeItem("todo_access_token");
  localStorage.removeItem("todo_current_user");
  els.sessionName.textContent = "Not signed in";
  els.sessionChip.classList.add("hidden");
  if (message) {
    setFeedback(message, true);
  }
  renderStats();
  renderProjects();
  renderTodos();
  showAuth();
}

function buildHeaders(includeJson = true) {
  const headers = {};
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  return headers;
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${DEFAULT_API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...buildHeaders(options.body !== undefined),
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    clearSession("Your session expired. Please sign in again.");
    throw new Error("Authentication required");
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep fallback detail if no JSON payload.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function renderStats() {
  els.statTotal.textContent = String(state.stats.total);
  els.statCompleted.textContent = String(state.stats.completed);
  els.statPending.textContent = String(state.stats.pending);
  els.statHighPriority.textContent = String(state.stats.high_priority);
}

function renderProjects() {
  els.projectList.innerHTML = "";

  const projectOptions = state.projects.map((project) => ({ value: project.id, label: project.name }));
  setSelectOptions(els.projectSelect, projectOptions, { includeEmpty: true, emptyLabel: "No project" });
  setSelectOptions(els.projectFilter, projectOptions, { includeEmpty: true, emptyLabel: "All projects" });
  setSelectOptions(els.editProjectId, projectOptions, { includeEmpty: true, emptyLabel: "No project" });

  if (!state.projects.length) {
    const empty = document.createElement("p");
    empty.className = "feedback";
    empty.textContent = "No projects yet. Create one to start sharing tasks.";
    els.projectList.append(empty);
    return;
  }

  state.projects.forEach((project) => {
    const node = els.projectTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".project-title").textContent = project.name;
    node.querySelector(".project-desc").textContent = project.description || "No description";
    node.querySelector(".project-members").textContent = `${project.members?.length || 0} member(s)`;
    node.querySelector(".project-owner").textContent = `Owner: ${getUserDisplayName(project.owner_id)}`;
    renderChipList(node.querySelector(".project-collaborators-list"), project.members || [], {
      className: "collaborator-chip",
      getLabel: (member) => member.name,
      onRemove: async (member) => {
        try {
          await apiRequest(`/api/v1/projects/${project.id}/members/${member.id}`, { method: "DELETE" });
          await refreshData();
          setFeedback(`${member.name} removed from project.`);
        } catch (error) {
          setFeedback(`Remove failed: ${error.message}`, true);
        }
      },
    });
    
    node.querySelector("button[data-action='edit']").addEventListener("click", () => openProjectDialog(project));
    node.querySelector("button[data-action='delete']").addEventListener("click", async () => {
      const confirmed = window.confirm(`Delete project \"${project.name}\"?`);
      if (!confirmed) {
        return;
      }
      try {
        await apiRequest(`/api/v1/projects/${project.id}`, { method: "DELETE" });
        await refreshData();
        setFeedback("Project deleted.");
      } catch (error) {
        setFeedback(`Delete failed: ${error.message}`, true);
      }
    });
    els.projectList.append(node);
  });
}

function openProjectDialog(project) {
  state.editingProjectId = project.id;
  els.editProjectName.value = project.name;
  els.editProjectDescription.value = project.description || "";
  
  // Render current members with remove buttons
  renderChipList(els.editProjectCurrentMembers, project.members || [], {
    className: "member-chip",
    getLabel: (member) => member.name,
    onRemove: async (member) => {
      try {
        await apiRequest(`/api/v1/projects/${project.id}/members/${member.id}`, { method: "DELETE" });
        // Refresh the dialog with updated project data
        await refreshData();
        const updatedProject = state.projects.find((p) => p.id === project.id);
        if (updatedProject) {
          openProjectDialog(updatedProject);
        }
        setFeedback(`${member.name} removed from project.`);
      } catch (error) {
        setFeedback(`Remove failed: ${error.message}`, true);
      }
    },
  });
  
  // Populate add collaborators select with all users
  setMultiSelectOptions(
    els.editProjectMemberIds,
    state.users.map((user) => ({ value: user.id, label: `${user.name} (${user.email})` })),
    [], // Don't pre-select anyone in the add section
  );
  els.projectDialog.showModal();
}

function closeProjectDialog() {
  state.editingProjectId = null;
  els.projectDialog.close();
}

function renderUsers() {
  const options = state.users.map((user) => ({ value: user.id, label: `${user.name} (${user.email})` }));
  setMultiSelectOptions(els.projectMemberIds, options);
  setMultiSelectOptions(els.todoAssigneeIds, options);
  setMultiSelectOptions(els.editAssigneeIds, options);
}

function renderUsersDialog() {
  els.usersList.innerHTML = "";
  state.users.forEach((user) => {
    const chip = document.createElement("div");
    chip.className = "member-chip";
    const label = document.createElement("span");
    label.textContent = `${user.name} (${user.email}) — ${user.role}`;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = user.role === "admin" ? "Demote" : "Promote";
    toggle.addEventListener("click", async () => {
      try {
        const newRole = user.role === "admin" ? "member" : "admin";
        await apiRequest(`/api/v1/users/${user.id}/role`, {
          method: "PATCH",
          body: JSON.stringify({ role: newRole }),
        });
        await refreshData();
        renderUsersDialog();
        setFeedback(`Updated role for ${user.name} to ${newRole}.`);
      } catch (err) {
        setFeedback(`Role update failed: ${err.message}`, true);
      }
    });
    chip.append(label, toggle);
    els.usersList.append(chip);
  });
}

function renderTodos() {
  els.todoList.innerHTML = "";

  if (!state.todos.length) {
    const empty = document.createElement("p");
    empty.className = "feedback";
    empty.textContent = "No tasks found for this filter set.";
    els.todoList.append(empty);
    return;
  }

  state.todos.forEach((todo) => {
    const node = els.template.content.firstElementChild.cloneNode(true);
    const title = node.querySelector(".todo-title");
    const desc = node.querySelector(".todo-desc");
    const meta = node.querySelector(".todo-meta");
    const people = node.querySelector(".todo-people");
    const badge = node.querySelector(".priority-badge");
    const toggle = node.querySelector("input[data-action='toggle']");
    const editBtn = node.querySelector("button[data-action='edit']");
    const deleteBtn = node.querySelector("button[data-action='delete']");

    title.textContent = todo.title;
    desc.textContent = todo.description?.trim() || "No description";
    badge.textContent = todo.priority;
    badge.classList.add(`priority-${todo.priority}`);
    meta.textContent = `Project: ${getProjectDisplayName(todo.project_id)} | Due: ${formatDate(todo.due_date)} | Updated: ${formatDate(todo.updated_at)}`;
    const assigneeNames = (todo.assignees || []).map((user) => user.name);
    people.textContent = assigneeNames.length ? `Assigned to: ${assigneeNames.join(", ")}` : "Unassigned";

    renderChipList(node.querySelector(".todo-assignees-list"), todo.assignees || [], {
      className: "assignee-chip",
      getLabel: (assignee) => assignee.name,
      onRemove: async (assignee) => {
        try {
          const newAssigneeIds = (todo.assignees || [])
            .filter((entry) => entry.id !== assignee.id)
            .map((entry) => entry.id);
          await apiRequest(`/api/v1/todos/${todo.id}`, {
            method: "PATCH",
            body: JSON.stringify({ assignee_ids: newAssigneeIds }),
          });
          await refreshData();
          setFeedback(`${assignee.name} removed from task.`);
        } catch (error) {
          setFeedback(`Remove failed: ${error.message}`, true);
        }
      },
    });

    toggle.checked = todo.completed;
    node.classList.toggle("completed", todo.completed);

    toggle.addEventListener("change", async () => {
      try {
        await apiRequest(`/api/v1/todos/${todo.id}`, {
          method: "PATCH",
          body: JSON.stringify({ completed: toggle.checked }),
        });
        await refreshData();
        setFeedback("Task status updated.");
      } catch (error) {
        setFeedback(`Update failed: ${error.message}`, true);
      }
    });

    editBtn.addEventListener("click", () => openEditDialog(todo));

    deleteBtn.addEventListener("click", async () => {
      const confirmed = window.confirm("Delete this task permanently?");
      if (!confirmed) {
        return;
      }
      try {
        await apiRequest(`/api/v1/todos/${todo.id}`, { method: "DELETE" });
        await refreshData();
        setFeedback("Task deleted.");
      } catch (error) {
        setFeedback(`Delete failed: ${error.message}`, true);
      }
    });

    els.todoList.append(node);
  });
}

function openEditDialog(todo) {
  state.editingTodoId = todo.id;
  state.editingTodo = todo;
  els.editTitle.value = todo.title;
  els.editDescription.value = todo.description || "";
  els.editPriority.value = todo.priority;
  els.editDueDate.value = toLocalDateTimeInputValue(todo.due_date);
  els.editProjectId.value = todo.project_id ? String(todo.project_id) : "";
  setMultiSelectOptions(
    els.editAssigneeIds,
    state.users.map((user) => ({ value: user.id, label: `${user.name} (${user.email})` })),
    (todo.assignees || []).map((user) => user.id),
  );
  els.editDialog.showModal();
}

function closeEditDialog() {
  state.editingTodoId = null;
  state.editingTodo = null;
  els.editDialog.close();
}

function buildTodoQuery() {
  const params = new URLSearchParams();
  params.set("skip", "0");
  params.set("limit", "100");
  params.set("sort_by", state.filters.sortBy);
  params.set("sort_order", state.filters.sortOrder);

  if (state.filters.search.trim()) {
    params.set("search", state.filters.search.trim());
  }
  if (state.filters.status === "completed") {
    params.set("completed", "true");
  }
  if (state.filters.status === "pending") {
    params.set("completed", "false");
  }
  if (state.filters.priority !== "all") {
    params.set("priority", state.filters.priority);
  }
  if (state.filters.projectId !== "all") {
    params.set("project_id", state.filters.projectId);
  }

  return params;
}

async function refreshData() {
  if (!state.token) {
    return;
  }

  try {
    const [usersPayload, projectsPayload, todosPayload, statsPayload] = await Promise.all([
      apiRequest("/api/v1/users?skip=0&limit=100"),
      apiRequest("/api/v1/projects"),
      apiRequest(`/api/v1/todos?${buildTodoQuery().toString()}`),
      apiRequest("/api/v1/todos/stats"),
    ]);

    state.users = usersPayload.items;
    state.projects = projectsPayload.items;
    state.todos = todosPayload.items;
    state.stats = statsPayload;

    renderUsers();
    renderProjects();
    renderTodos();
    renderStats();
  } catch (error) {
    setFeedback(`Could not load data: ${error.message}`, true);
  }
}

function setupAuthHandlers() {
  setAuthMode(state.authMode);

  els.loginTabBtn.addEventListener("click", () => setAuthMode("login"));
  els.registerTabBtn.addEventListener("click", () => setAuthMode("register"));
  els.googleSignInBtn.addEventListener("click", () => {
    window.location.href = `${DEFAULT_API_BASE_URL}/api/v1/auth/google`;
  });

  els.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = els.authEmail.value.trim();
    const password = els.authPassword.value;
    const isRegister = state.authMode === "register";
    const payload = isRegister
      ? {
          name: els.authName.value.trim(),
          email,
          password,
        }
      : {
          email,
          password,
        };

    if (isRegister && !payload.name) {
      setFeedback("Name is required for registration.", true);
      return;
    }

    try {
      const response = await apiRequest(`/api/v1/auth/${isRegister ? "register" : "login"}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSession(response.access_token, response.user);
      els.authForm.reset();
      setAuthMode("login");
      setFeedback(isRegister ? "Account created. Welcome." : "Signed in.");
      await refreshData();
    } catch (error) {
      setFeedback(`Authentication failed: ${error.message}`, true);
    }
  });

  els.signOutBtn.addEventListener("click", () => {
    clearSession("Signed out.");
  });
}

function setupProjectHandler() {
  els.projectForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const name = els.projectName.value.trim();
    if (!name) {
      setFeedback("Project name is required.", true);
      return;
    }

    try {
      await apiRequest("/api/v1/projects", {
        method: "POST",
        body: JSON.stringify({
          name,
          description: els.projectDescription.value.trim() || null,
          member_ids: selectedValues(els.projectMemberIds),
        }),
      });
      els.projectForm.reset();
      await refreshData();
      setFeedback("Project created.");
    } catch (error) {
      setFeedback(`Project creation failed: ${error.message}`, true);
    }
  });
}

function setupProjectEditHandlers() {
  els.projectEditForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!state.editingProjectId) {
      setFeedback("No selected project to update.", true);
      return;
    }

    const name = els.editProjectName.value.trim();
    if (!name) {
      setFeedback("Project name is required.", true);
      return;
    }

    try {
      // Update project name and description
      await apiRequest(`/api/v1/projects/${state.editingProjectId}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          description: els.editProjectDescription.value.trim() || null,
        }),
      });

      // Add any newly selected members
      const newMemberIds = Array.from(els.editProjectMemberIds.selectedOptions).map((option) => Number(option.value));
      if (newMemberIds.length > 0) {
        await apiRequest(`/api/v1/projects/${state.editingProjectId}/members`, {
          method: "POST",
          body: JSON.stringify({ member_ids: newMemberIds }),
        });
      }

      closeProjectDialog();
      await refreshData();
      setFeedback("Project updated.");
    } catch (error) {
      setFeedback(`Project update failed: ${error.message}`, true);
    }
  });

  els.cancelProjectEditBtn.addEventListener("click", () => closeProjectDialog());
}

function setupUserManagementHandlers() {
  els.manageUsersBtn?.addEventListener("click", () => {
    renderUsersDialog();
    els.usersDialog.showModal();
  });

  els.closeUsersBtn?.addEventListener("click", () => {
    els.usersDialog.close();
  });
}

function setupTodoHandlers() {
  els.todoForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const title = els.title.value.trim();
    if (!title) {
      setFeedback("Title is required.", true);
      return;
    }

    try {
      await apiRequest("/api/v1/todos", {
        method: "POST",
        body: JSON.stringify({
          title,
          description: els.description.value.trim() || null,
          completed: false,
          priority: els.priority.value,
          due_date: fromInputDateToIso(els.dueDate.value),
          project_id: els.projectSelect.value ? Number(els.projectSelect.value) : null,
          assignee_ids: selectedValues(els.todoAssigneeIds),
        }),
      });
      els.todoForm.reset();
      els.priority.value = "medium";
      els.projectSelect.value = "";
      await refreshData();
      setFeedback("Task created.");
    } catch (error) {
      setFeedback(`Create failed: ${error.message}`, true);
    }
  });
}

function setupEditDialogHandlers() {
  els.editForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!state.editingTodoId) {
      setFeedback("No selected task to update.", true);
      return;
    }

    const title = els.editTitle.value.trim();
    if (!title) {
      setFeedback("Title is required.", true);
      return;
    }

    try {
      await apiRequest(`/api/v1/todos/${state.editingTodoId}`, {
        method: "PATCH",
        body: JSON.stringify({
          title,
          description: els.editDescription.value.trim() || null,
          priority: els.editPriority.value,
          due_date: fromInputDateToIso(els.editDueDate.value),
          project_id: els.editProjectId.value ? Number(els.editProjectId.value) : null,
          assignee_ids: selectedValues(els.editAssigneeIds),
        }),
      });
      closeEditDialog();
      await refreshData();
      setFeedback("Task updated.");
    } catch (error) {
      setFeedback(`Update failed: ${error.message}`, true);
    }
  });

  els.cancelEditBtn.addEventListener("click", () => closeEditDialog());
}

function setupFilterHandlers() {
  let searchDebounce = null;

  els.searchInput.addEventListener("input", () => {
    state.filters.search = els.searchInput.value;
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      refreshData();
    }, 250);
  });

  els.statusFilter.addEventListener("change", () => {
    state.filters.status = els.statusFilter.value;
    refreshData();
  });

  els.priorityFilter.addEventListener("change", () => {
    state.filters.priority = els.priorityFilter.value;
    refreshData();
  });

  els.projectFilter.addEventListener("change", () => {
    state.filters.projectId = els.projectFilter.value || "all";
    refreshData();
  });

  els.sortBy.addEventListener("change", () => {
    state.filters.sortBy = els.sortBy.value;
    refreshData();
  });

  els.sortOrder.addEventListener("change", () => {
    state.filters.sortOrder = els.sortOrder.value;
    refreshData();
  });
}

async function bootstrapSession() {
  const oauthReturn = parseOAuthReturn();
  if (oauthReturn) {
    setSession(oauthReturn.accessToken, oauthReturn.user);
    window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    await refreshData();
    return;
  }

  if (!state.token) {
    els.sessionName.textContent = "Not signed in";
    showAuth();
    return;
  }

  try {
    const user = await apiRequest("/api/v1/auth/me");
    setSession(state.token, user);
    await refreshData();
  } catch {
    clearSession("Please sign in again.");
  }
}

function initialize() {
  setupAuthHandlers();
  setupProjectHandler();
  setupProjectEditHandlers();
  setupUserManagementHandlers();
  setupTodoHandlers();
  setupEditDialogHandlers();
  setupFilterHandlers();
  els.refreshBtn.addEventListener("click", async () => {
    setFeedback("Refreshing...");
    await refreshData();
    setFeedback("Data refreshed.");
  });

  showAuth();
  bootstrapSession();
}

initialize();
