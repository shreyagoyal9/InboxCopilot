import { useEffect, useState } from "react";
import { signInWithPopup, signOut, onAuthStateChanged } from "firebase/auth";
import {
  doc,
  getDoc,
  setDoc,
  serverTimestamp,
  collection,
  addDoc,
  onSnapshot,
  deleteDoc,
  updateDoc,
} from "firebase/firestore";
import {
  auth,
  db,
  googleProvider,
  GOOGLE_OAUTH_CLIENT_ID,
  GMAIL_READONLY_SCOPE,
} from "./firebase";
import "./App.css";

const REDIRECT_URI = window.location.origin + window.location.pathname;

const FREQUENCY_OPTIONS = [
  { label: "Every 5 minutes", minutes: 5 },
  { label: "Every 15 minutes", minutes: 15 },
  { label: "Every 30 minutes", minutes: 30 },
  { label: "Hourly", minutes: 60 },
  { label: "Daily", minutes: 1440 },
];

const DURATION_OPTIONS = [
  { label: "1 week", days: 7 },
  { label: "1 month", days: 30 },
  { label: "3 months", days: 90 },
  { label: "6 months", days: 180 },
  { label: "Until I stop it", days: null },
];

const CHANNEL_OPTIONS = [
  { value: "email", label: "Email only" },
  { value: "whatsapp", label: "WhatsApp only" },
  { value: "both", label: "Email + WhatsApp" },
];

function buildGmailAuthUrl(uid) {
  const params = new URLSearchParams({
    client_id: GOOGLE_OAUTH_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: GMAIL_READONLY_SCOPE,
    access_type: "offline",
    prompt: "consent",
    state: uid,
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setAuthLoading(false);
    });
    return unsub;
  }, []);

  useEffect(() => {
    if (!user) {
      setProfile(null);
      return;
    }
    setProfileLoading(true);
    getDoc(doc(db, "users", user.uid)).then((snap) => {
      setProfile(snap.exists() ? snap.data() : null);
      setProfileLoading(false);
    });
  }, [user]);

  // Handle redirect back from Google's Gmail consent screen
  useEffect(() => {
    if (!user) return;
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (code && state === user.uid) {
      (async () => {
        await setDoc(
          doc(db, "users", user.uid),
          {
            email: user.email,
            gmailPendingCode: code,
            gmailPendingCodeAt: serverTimestamp(),
            gmailRedirectUri: REDIRECT_URI,
            gmailConnected: false,
            updatedAt: serverTimestamp(),
          },
          { merge: true }
        );
        window.history.replaceState({}, "", window.location.pathname);
        const snap = await getDoc(doc(db, "users", user.uid));
        setProfile(snap.data());
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  async function handleSignIn() {
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      console.error(err);
      alert("Sign-in didn't go through. Try again?");
    }
  }

  async function handleConnectGmail() {
    await setDoc(
      doc(db, "users", user.uid),
      { email: user.email, updatedAt: serverTimestamp() },
      { merge: true }
    );
    window.location.href = buildGmailAuthUrl(user.uid);
  }

  if (authLoading) {
    return <div className="ic-shell ic-center">Loading…</div>;
  }

  if (!user) {
    return <Landing onSignIn={handleSignIn} />;
  }

  if (profileLoading) {
    return <div className="ic-shell ic-center">Loading your setup…</div>;
  }

  const gmailConnected = Boolean(profile?.gmailPendingCode);

  return (
    <div className="ic-shell">
      <TopBar email={user.email} onSignOut={() => signOut(auth)} />
      {gmailConnected ? (
        <TasksDashboard uid={user.uid} />
      ) : (
        <ConnectGmail onConnect={handleConnectGmail} />
      )}
    </div>
  );
}

function TopBar({ email, onSignOut }) {
  return (
    <header className="ic-topbar">
      <span className="ic-wordmark">InboxCopilot</span>
      <div className="ic-topbar-right">
        <span className="ic-email">{email}</span>
        <button className="ic-link-btn" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </header>
  );
}

function Landing({ onSignIn }) {
  return (
    <div className="ic-shell ic-landing">
      <a
        className="ic-github-link"
        href="https://github.com/shreyagoyal9/InboxCopilot"
        target="_blank"
        rel="noreferrer"
      >
        View source on GitHub ↗
      </a>
      <div className="ic-landing-inner">
        <div className="ic-eyebrow">for inboxes that bury the one line that matters</div>
        <h1 className="ic-hero">
          Read the reply.
          <br />
          Skip the thread.
        </h1>
        <p className="ic-sub">
          InboxCopilot watches any sender on your behalf, reads full threads
          — trailing replies included — and alerts you only when something
          you actually care about shows up.
        </p>
        <button className="ic-cta" onClick={onSignIn}>
          Sign in with Google
        </button>
        <p className="ic-fineprint">
          Read-only Gmail access. We never send mail on your behalf.
        </p>

        <div className="ic-steps">
          <div className="ic-step">
            <span className="ic-step-num">01</span>
            <span className="ic-step-text">Connect Gmail, read-only</span>
          </div>
          <div className="ic-step">
            <span className="ic-step-num">02</span>
            <span className="ic-step-text">Tell it who to watch, and for what</span>
          </div>
          <div className="ic-step">
            <span className="ic-step-num">03</span>
            <span className="ic-step-text">Get pinged the moment it matters</span>
          </div>
        </div>

        <div className="ic-stack-strip">
          Firebase Auth · Firestore · Gmail API · GitHub Actions —{" "}
          <span className="ic-stack-highlight">$0/month, no billing account, ever</span>
        </div>
      </div>
    </div>
  );
}

function ConnectGmail({ onConnect }) {
  return (
    <div className="ic-onboarding">
      <div className="ic-card">
        <div className="ic-step-label">One-time setup</div>
        <h2 className="ic-card-title">Connect your inbox</h2>
        <p className="ic-card-hint">
          Read-only access, connected once. After this you can create as
          many watch tasks as you like — no need to reconnect.
        </p>
        <button className="ic-cta ic-cta-full" onClick={onConnect}>
          Connect Gmail
        </button>
      </div>
    </div>
  );
}

function TasksDashboard({ uid }) {
  const [tasks, setTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const unsub = onSnapshot(collection(db, "users", uid, "tasks"), (snap) => {
      const list = snap.docs.map((d) => ({ id: d.id, ...d.data() }));
      list.sort((a, b) => (b.createdAtMs || 0) - (a.createdAtMs || 0));
      setTasks(list);
      setTasksLoading(false);
    });
    return unsub;
  }, [uid]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 6000);
    return () => clearTimeout(t);
  }, [toast]);

  async function handleCreateTask(taskData) {
    await addDoc(collection(db, "users", uid, "tasks"), {
      ...taskData,
      active: true,
      createdAt: serverTimestamp(),
      createdAtMs: Date.now(),
    });
    setShowForm(false);
    setToast(
      `Task created — watching for "${taskData.keyword}" from ${taskData.sender}. You'll be alerted once the watcher's next scheduled check finds a match.`
    );
  }

  async function handleToggleActive(task) {
    await updateDoc(doc(db, "users", uid, "tasks", task.id), {
      active: !task.active,
    });
  }

  async function handleDeleteTask(task) {
    if (!confirm(`Stop watching for "${task.keyword}"? This can't be undone.`)) return;
    await deleteDoc(doc(db, "users", uid, "tasks", task.id));
  }

  return (
    <div className="ic-dashboard">
      {toast && (
        <div className="ic-toast">
          <span className="ic-toast-check">✓</span>
          <span>{toast}</span>
        </div>
      )}
      <div className="ic-dashboard-header">
        <div>
          <h2 className="ic-dashboard-title">Your watch tasks</h2>
          <p className="ic-dashboard-sub">
            Each task watches one sender for one thing you care about.
          </p>
        </div>
        {!showForm && (
          <button className="ic-cta" onClick={() => setShowForm(true)}>
            + New watch task
          </button>
        )}
      </div>

      {showForm && (
        <TaskForm onCancel={() => setShowForm(false)} onSubmit={handleCreateTask} />
      )}

      {tasksLoading ? (
        <p className="ic-card-hint">Loading your tasks…</p>
      ) : tasks.length === 0 && !showForm ? (
        <EmptyState onCreate={() => setShowForm(true)} />
      ) : (
        <div className="ic-task-list">
          {tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              onToggle={() => handleToggleActive(task)}
              onDelete={() => handleDeleteTask(task)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState({ onCreate }) {
  return (
    <div className="ic-empty">
      <p className="ic-card-hint">
        No watch tasks yet. A task might be "alert me when my placement
        office emails about Batch A" — or just as easily "alert me when my
        manager emails about the Q3 review."
      </p>
      <button className="ic-cta" onClick={onCreate}>
        Create your first task
      </button>
    </div>
  );
}

function TaskForm({ onCancel, onSubmit }) {
  const [sender, setSender] = useState("");
  const [keyword, setKeyword] = useState("");
  const [channel, setChannel] = useState("email");
  const [whatsapp, setWhatsapp] = useState("");
  const [frequency, setFrequency] = useState(FREQUENCY_OPTIONS[2].minutes);
  const [duration, setDuration] = useState(DURATION_OPTIONS[1].days);
  const [saving, setSaving] = useState(false);

  async function handleSubmit() {
    if (!sender.trim()) return alert("Enter the sender's email address.");
    if (!keyword.trim()) return alert("Enter what to watch for.");
    if (channel !== "email" && !whatsapp.trim())
      return alert("Enter your WhatsApp number, or switch to Email only.");

    setSaving(true);
    await onSubmit({
      sender: sender.trim().toLowerCase(),
      keyword: keyword.trim(),
      alertChannel: channel,
      whatsappNumber: channel !== "email" ? whatsapp.trim() : null,
      frequencyMinutes: frequency,
      durationDays: duration,
    });
    setSaving(false);
  }

  return (
    <div className="ic-card ic-form-card">
      <div className="ic-form-row">
        <label className="ic-label">Sender to watch</label>
        <input
          className="ic-input"
          type="email"
          placeholder="e.g. placements@yourcollege.edu or boss@company.com"
          value={sender}
          onChange={(e) => setSender(e.target.value)}
        />
      </div>

      <div className="ic-form-row">
        <label className="ic-label">What to watch for</label>
        <input
          className="ic-input"
          type="text"
          placeholder='e.g. "Batch A", "Q3 review", "my team"'
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </div>

      <div className="ic-form-row-split">
        <div className="ic-form-row">
          <label className="ic-label">Check how often</label>
          <select
            className="ic-input"
            value={frequency}
            onChange={(e) => setFrequency(Number(e.target.value))}
          >
            {FREQUENCY_OPTIONS.map((opt) => (
              <option key={opt.minutes} value={opt.minutes}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="ic-form-row">
          <label className="ic-label">Run for</label>
          <select
            className="ic-input"
            value={duration ?? "forever"}
            onChange={(e) =>
              setDuration(e.target.value === "forever" ? null : Number(e.target.value))
            }
          >
            {DURATION_OPTIONS.map((opt) => (
              <option key={opt.label} value={opt.days ?? "forever"}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="ic-form-row">
        <label className="ic-label">Alert me by</label>
        <div className="ic-radio-group">
          {CHANNEL_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`ic-radio ${channel === opt.value ? "ic-radio-active" : ""}`}
            >
              <input
                type="radio"
                name="channel"
                checked={channel === opt.value}
                onChange={() => setChannel(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
        {channel !== "email" && (
          <input
            className="ic-input ic-input-spaced"
            type="tel"
            placeholder="e.g. +91 98765 43210"
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
          />
        )}
      </div>

      <div className="ic-form-actions">
        <button className="ic-link-btn" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button className="ic-cta" onClick={handleSubmit} disabled={saving}>
          {saving ? "Saving…" : "Start watching"}
        </button>
      </div>
    </div>
  );
}

function TaskRow({ task, onToggle, onDelete }) {
  const freqLabel =
    FREQUENCY_OPTIONS.find((f) => f.minutes === task.frequencyMinutes)?.label ||
    `Every ${task.frequencyMinutes} min`;
  const durLabel =
    task.durationDays == null
      ? "Until stopped"
      : DURATION_OPTIONS.find((d) => d.days === task.durationDays)?.label ||
        `${task.durationDays} days`;

  const channelLabel =
    CHANNEL_OPTIONS.find((c) => c.value === task.alertChannel)?.label || "Email only";

  return (
    <div className={`ic-task-row ${task.active ? "" : "ic-task-row-paused"}`}>
      <div className="ic-task-main">
        <div className="ic-task-keyword">{task.keyword}</div>
        <div className="ic-task-meta">
          from <span className="ic-task-sender">{task.sender}</span> · {freqLabel} ·{" "}
          {durLabel} · {channelLabel}
        </div>
      </div>
      <div className="ic-task-actions">
        <button className="ic-link-btn" onClick={onToggle}>
          {task.active ? "Pause" : "Resume"}
        </button>
        <button className="ic-link-btn ic-link-btn-danger" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  );
}
