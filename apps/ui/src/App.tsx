import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

type Role = "user" | "assistant" | "system";

type Message = {
	id: string;
	role: Role;
	content: string;
	created_at: string;
	spoken: boolean;
};

type Conversation = {
	id: string;
	title: string;
	provider: string;
	state: string;
	messages: Message[];
};

type TurnResponse = {
	conversation: Conversation;
	reply: Message;
};

function App() {
	const [conversation, setConversation] = useState<Conversation | null>(null);
	const [draft, setDraft] = useState("");
	const [runtimeStatus, setRuntimeStatus] = useState<
		"checking" | "online" | "offline"
	>("checking");
	const [error, setError] = useState<string | null>(null);
	const [sending, setSending] = useState(false);
	const messageEndRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		let active = true;

		async function initialize() {
			try {
				const healthResponse = await fetch("/health");
				if (!healthResponse.ok) throw new Error("Runtime health check failed");
				if (active) setRuntimeStatus("online");

				const conversationResponse = await fetch("/api/conversations", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ title: "New conversation", provider: "fake" }),
				});
				if (!conversationResponse.ok)
					throw new Error("Could not start a conversation");
				const created = (await conversationResponse.json()) as Conversation;
				if (active) setConversation(created);
			} catch (reason) {
				if (!active) return;
				setRuntimeStatus("offline");
				setError(
					reason instanceof Error ? reason.message : "Elena is unavailable",
				);
			}
		}

		void initialize();
		return () => {
			active = false;
		};
	}, []);

	useEffect(() => {
		messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [conversation?.messages, sending]);

	async function sendMessage(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const content = draft.trim();
		if (!conversation || !content || sending) return;

		setDraft("");
		setError(null);
		setSending(true);
		const optimisticMessage: Message = {
			id: crypto.randomUUID(),
			role: "user",
			content,
			created_at: new Date().toISOString(),
			spoken: false,
		};
		setConversation({
			...conversation,
			state: "thinking",
			messages: [...conversation.messages, optimisticMessage],
		});

		try {
			const response = await fetch(
				`/api/conversations/${conversation.id}/messages`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ content }),
				},
			);
			if (!response.ok)
				throw new Error("The runtime could not complete that turn");
			const result = (await response.json()) as TurnResponse;
			setConversation(result.conversation);
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : "The request failed");
			setConversation(
				(current) => current && { ...current, state: "blocked_actionable" },
			);
		} finally {
			setSending(false);
		}
	}

	const hasMessages = Boolean(conversation?.messages.length);
	const isWorking = sending || conversation?.state === "thinking";

	return (
		<div className="app-shell">
			<aside className="identity-panel">
				<header className="brand">
					<span className="brand-mark">E</span>
					<div>
						<strong>Elena</strong>
						<span>Personal attendant</span>
					</div>
				</header>

				<div
					className={`portrait ${isWorking ? "is-thinking" : ""}`}
					aria-label={isWorking ? "Elena is thinking" : "Elena is ready"}
				>
					<div className="shoulders" />
					<div className="hair-back" />
					<div className="neck" />
					<div className="face">
						<div className="hair-crown" />
						<div className="hair-side hair-side-left" />
						<div className="hair-side hair-side-right" />
						<div className="brow brow-left" />
						<div className="brow brow-right" />
						<div className="eye eye-left" />
						<div className="eye eye-right" />
						<div className="cheek cheek-left" />
						<div className="cheek cheek-right" />
						<div className="nose" />
						<div className="mouth" />
					</div>
				</div>

				<div className="presence">
					<span className={`status-light status-${runtimeStatus}`} />
					<div>
						<strong>
							{runtimeStatus === "online"
								? "At your service"
								: runtimeStatus === "checking"
									? "Preparing"
									: "Runtime offline"}
						</strong>
						<span>
							{isWorking
								? "Considering your request"
								: "Local development mode"}
						</span>
					</div>
				</div>

				<nav className="sidebar-nav" aria-label="Elena sections">
					<button className="nav-item is-active" type="button">
						<span aria-hidden="true">01</span> Conversation
					</button>
					<button className="nav-item" type="button" disabled>
						<span aria-hidden="true">02</span> Tasks
					</button>
					<button className="nav-item" type="button" disabled>
						<span aria-hidden="true">03</span> Memory
					</button>
					<button className="nav-item" type="button" disabled>
						<span aria-hidden="true">04</span> Skills
					</button>
				</nav>

				<div className="provider-note">
					<span>Provider</span>
					<strong>{conversation?.provider ?? "fake"}</strong>
				</div>
			</aside>

			<main className="conversation-panel">
				<header className="conversation-header">
					<div>
						<span className="eyebrow">Private conversation</span>
						<h1>{conversation?.title ?? "New conversation"}</h1>
					</div>
					<button
						className="icon-button"
						type="button"
						aria-label="Start a new conversation"
						title="New conversation"
						disabled
					>
						<span aria-hidden="true">+</span>
					</button>
				</header>

				<section
					className={`message-list ${hasMessages ? "" : "is-empty"}`}
					aria-live="polite"
				>
					{!hasMessages && (
						<div className="welcome">
							<span className="welcome-rule" />
							<p>Good day.</p>
							<h2>What shall we attend to?</h2>
							<p className="welcome-copy">
								I am running with the deterministic development provider. We can
								exercise conversation and persistence without contacting an
								external model.
							</p>
						</div>
					)}

					{conversation?.messages.map((message) => (
						<article
							key={message.id}
							className={`message message-${message.role}`}
						>
							<span className="message-author">
								{message.role === "assistant" ? "Elena" : "You"}
							</span>
							<p>{message.content}</p>
							{message.role === "assistant" && (
								<details className="activity-summary">
									<summary>Activity</summary>
									<span>
										Response generated by the {conversation.provider} provider
										and saved to the local conversation archive.
									</span>
								</details>
							)}
						</article>
					))}

					{sending && (
						<div className="working-line" role="status">
							<span />
							<span />
							<span />
							<p>One moment. I am considering that.</p>
						</div>
					)}
					<div ref={messageEndRef} />
				</section>

				<footer className="composer-area">
					{error && (
						<p className="error-banner" role="alert">
							{error}
						</p>
					)}
					<form className="composer" onSubmit={sendMessage}>
						<label htmlFor="message-input">Message Elena</label>
						<textarea
							id="message-input"
							value={draft}
							onChange={(event) => setDraft(event.target.value)}
							onKeyDown={(event) => {
								if (event.key === "Enter" && !event.shiftKey) {
									event.preventDefault();
									event.currentTarget.form?.requestSubmit();
								}
							}}
							placeholder={
								runtimeStatus === "online"
									? "How may I help?"
									: "Waiting for the local runtime..."
							}
							rows={2}
							disabled={runtimeStatus !== "online" || !conversation || sending}
						/>
						<button
							type="submit"
							disabled={!draft.trim() || !conversation || sending}
						>
							Send
						</button>
					</form>
					<p className="privacy-note">
						Development mode. No external model is contacted.
					</p>
				</footer>
			</main>
		</div>
	);
}

export default App;
