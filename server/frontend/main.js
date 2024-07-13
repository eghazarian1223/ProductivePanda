const todoInput = document.querySelector(".todo-input");
const addTodoButton = document.querySelector(".todo-button");
const todoList = document.querySelector(".todo-list");
const filterDropdownMenu = document.querySelector(".filter-todo");

document.addEventListener("DOMContentLoaded", getLocalTodos); 
addTodoButton.addEventListener("click", addTodoItem);
todoList.addEventListener("click", handleTodoButtonClick);
filterDropdownMenu.addEventListener("change", filterTodosByStatus);

// Creates a new todo item and adds it to the local storage and DOM
function addTodoItem() {
    const todoItemDiv = document.createElement("div"); 
    todoItemDiv.classList.add("todo");
    const newTodo = document.createElement("li");
    newTodo.innerText = todoInput.value;
    newTodo.classList.add("todo-item");
    todoItemDiv.appendChild(newTodo); 
    const newTodoObject = addTodoToLocalStorage(todoInput.value); 
    todoItemDiv.id = newTodoObject.id 

    const orangeCheckMarkButton = document.createElement("Button");
    orangeCheckMarkButton.innerHTML = '<i class="fas fa-check-circle"></i>';
    orangeCheckMarkButton.classList.add("check-mark-btn");
    todoItemDiv.appendChild(orangeCheckMarkButton);

    const grayTrashButton = document.createElement("button");
    grayTrashButton.innerHTML = '<i class="fas fa-trash"></i>';
    grayTrashButton.classList.add("trash-btn");
    todoItemDiv.appendChild(grayTrashButton);
    todoList.appendChild(todoItemDiv); 
    todoInput.value = ""; // Clear the input field to prepare for the next entry
}
// Deletes or marks a to-do item as complete based on the button clicked
function handleTodoButtonClick(e) {   
    const clickedItem = e.target; 
    if (clickedItem.classList[0] === "trash-btn") {
        const todoItemDiv = clickedItem.parentElement; 
        todoItemDiv.classList.add("slide"); 
        removeLocalTodoItems(todoItemDiv.id); 
        todoItemDiv.addEventListener("transitionend", function () {
            todoItemDiv.remove(); 
        });
    }

    if (clickedItem.classList.contains("check-mark-btn")) {
        const todo = clickedItem.parentElement;
        updateLocalTodos(todo.id);
        todo.classList.toggle("finished");
    }

}
// This function manages the display of todo items based on the chosen dropdown option
function filterTodosByStatus(e) { 
    const todos = todoList.childNodes; 
    localStorage.setItem("dropdownStatus", e.target.value)
    todos.forEach(function (todo) {
        switch (e.target.value) {  // Switch statement to handle different cases based on dropdownStatus(all, finished, or awaiting)
            case "all":
                todo.style.display = "flex";
                break; 
            case "finished":
                if (todo.classList.contains("finished")) {
                    todo.style.display = "flex";  // This line allows the CSS portion .finished to play out 
                } else {
                    todo.style.display = "none";
                }
                break;
            case "awaiting":
                if (!todo.classList.contains("finished")) {
                    todo.style.display = "flex";
                } else {
                    todo.style.display = "none";
                }
                break;
        }
    });
}

// Adds a new to-do item to local storage and returns the to-do object
function addTodoToLocalStorage(todo) {
    let todos;  
    if (localStorage.getItem("todos") === null) {
        todos = [];
    } else {
        todos = JSON.parse(localStorage.getItem("todos"));
    }
    const todoObject = { text: todo, status: "awaiting", id: new Date().getTime() } // Generates unique ID for each todo item based on the current timestamp
    todos.push(todoObject);
    localStorage.setItem("todos", JSON.stringify(todos));
    return todoObject
}
// Retrieves to-do items from local storage and displays them based on dropdown status.
function getLocalTodos() {
    let todos; 
    let dropdownStatus = localStorage.getItem("dropdownStatus");
    if (dropdownStatus !== null) {
        filterDropdownMenu.value = dropdownStatus;
    }
    if (localStorage.getItem("todos") === null) {
        todos = [];
    } else {
        todos = JSON.parse(localStorage.getItem("todos"));
    }
    // Function to create and display a single to-do item
    function createAndDisplayTodoItem(todoObject) {
        const todoItemDiv = document.createElement("div");
                todoItemDiv.classList.add("todo");
                const newTodo = document.createElement("li");
                if (dropdownStatus === null || dropdownStatus === "all" || dropdownStatus === todoObject.status) {
                    todoItemDiv.style.display = "flex";
                } else {
                    todoItemDiv.style.display = "none";
                }
                newTodo.innerText = todoObject.text; 
                newTodo.classList.add("todo-item");
                todoItemDiv.appendChild(newTodo);
                todoItemDiv.id = todoObject.id;
                if (todoObject.status === "finished") {
                    todoItemDiv.classList.add("finished");
                }
            const orangeCheckMarkButton = document.createElement("button");
            orangeCheckMarkButton.innerHTML = '<i class="fas fa-check-circle"></i>';
            orangeCheckMarkButton.classList.add("check-mark-btn");
            todoItemDiv.appendChild(orangeCheckMarkButton);

            const grayTrashButton = document.createElement("button");
            grayTrashButton.innerHTML = '<i class="fas fa-trash"></i>';
            grayTrashButton.classList.add("trash-btn");
            todoItemDiv.appendChild(grayTrashButton);

            todoList.appendChild(todoItemDiv);
        }
        todos.forEach(createAndDisplayTodoItem);
}

// Removes a todo item from local storage based on its ID
function removeLocalTodoItems(todoId) {
    let todos;
    if (localStorage.getItem("todos") === null) {
        todos = [];
    } else {
        todos = JSON.parse(localStorage.getItem("todos"));
    }
    const updateTodos = todos.filter(function (todoObject) {
        return todoId != todoObject.id

    });

    localStorage.setItem("todos", JSON.stringify(updateTodos));
}

// Updates the status of a todo item in local storage based on its ID
function updateLocalTodos(todoId) {
    let todos;
    if (localStorage.getItem("todos") === null) {
        todos = [];
    } else {
        todos = JSON.parse(localStorage.getItem("todos"));
    }
    // Iterates through each todo item; if its ID matches the given ID, toggles its status, creating a new array with updated todo items.
    const updatedTodos = todos.map(function (todoObject) {
        if (todoId == todoObject.id) {
            let currentStatus = todoObject.status;
            todoObject.status = currentStatus === "awaiting" ? "finished" : "awaiting" 
           
        }
        return todoObject 

    });
    localStorage.setItem("todos", JSON.stringify(updatedTodos)); 

}