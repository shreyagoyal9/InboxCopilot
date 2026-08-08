// Firebase config values are safe to keep in frontend code — they identify
// the project, they are not secrets. Real access control happens through
// Firebase Auth + Firestore security rules, not by hiding these values.
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyBX3xA2VwYHUvQumHbIp4imksOcAomjcoc",
  authDomain: "inboxcopilot-503909.firebaseapp.com",
  projectId: "inboxcopilot-503909",
  storageBucket: "inboxcopilot-503909.firebasestorage.app",
  messagingSenderId: "567539804836",
  appId: "1:567539804836:web:c4245feb58e756189ed431",
  measurementId: "G-XVB823CFKP",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

// This is the OAuth Web Client we created in the Google Cloud console
// (Task 3 -> Clients). It's used for the separate "Connect Gmail" step,
// which is a different flow from Firebase's own Google Sign-In, because
// we need an offline (refresh-capable) grant for gmail.readonly.
export const GOOGLE_OAUTH_CLIENT_ID =
  "567539804836-c37vlf72fu226s81nsvutm3b7pb8rpo5.apps.googleusercontent.com";

export const GMAIL_READONLY_SCOPE =
  "https://www.googleapis.com/auth/gmail.readonly";
