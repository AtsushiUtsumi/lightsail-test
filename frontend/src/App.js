import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = 'http://localhost:8000/api/todos/';

function App() {
  const [todos, setTodos] = useState([]);
  const [newTodo, setNewTodo] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTodos();
  }, []);

  const fetchTodos = async () => {
    try {
      setLoading(true);
      const response = await axios.get(API_URL);
      setTodos(response.data);
      setError(null);
    } catch (err) {
      setError('Todoの読み込みに失敗しました');
      console.error('Error fetching todos:', err);
    } finally {
      setLoading(false);
    }
  };

  const addTodo = async (e) => {
    e.preventDefault();
    if (!newTodo.trim()) return;

    try {
      const response = await axios.post(API_URL, {
        title: newTodo,
        completed: false
      });
      setTodos([response.data, ...todos]);
      setNewTodo('');
      setError(null);
    } catch (err) {
      setError('Todoの追加に失敗しました');
      console.error('Error adding todo:', err);
    }
  };

  const toggleTodo = async (id, completed) => {
    try {
      const response = await axios.patch(`${API_URL}${id}/`, {
        completed: !completed
      });
      setTodos(todos.map(todo =>
        todo.id === id ? response.data : todo
      ));
      setError(null);
    } catch (err) {
      setError('Todoの更新に失敗しました');
      console.error('Error updating todo:', err);
    }
  };

  const deleteTodo = async (id) => {
    try {
      await axios.delete(`${API_URL}${id}/`);
      setTodos(todos.filter(todo => todo.id !== id));
      setError(null);
    } catch (err) {
      setError('Todoの削除に失敗しました');
      console.error('Error deleting todo:', err);
    }
  };

  return (
    <div className="App">
      <div className="todo-container">
        <h1>Todo List</h1>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={addTodo} className="todo-form">
          <input
            type="text"
            value={newTodo}
            onChange={(e) => setNewTodo(e.target.value)}
            placeholder="新しいTodoを入力..."
            className="todo-input"
          />
          <button type="submit" className="add-button">追加</button>
        </form>

        {loading ? (
          <div className="loading">読み込み中...</div>
        ) : (
          <ul className="todo-list">
            {todos.length === 0 ? (
              <li className="empty-message">Todoがありません</li>
            ) : (
              todos.map(todo => (
                <li key={todo.id} className="todo-item">
                  <div className="todo-content">
                    <input
                      type="checkbox"
                      checked={todo.completed}
                      onChange={() => toggleTodo(todo.id, todo.completed)}
                      className="todo-checkbox"
                    />
                    <span className={todo.completed ? 'completed' : ''}>
                      {todo.title}
                    </span>
                  </div>
                  <button
                    onClick={() => deleteTodo(todo.id)}
                    className="delete-button"
                  >
                    削除
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  );
}

export default App;
