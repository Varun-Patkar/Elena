import { useState } from "react";
import type { FormEvent } from "react";

export type ProviderSettings = {
	setup_complete: boolean;
	selected_provider: "fake" | "lmstudio" | "copilot";
	lmstudio_url: string;
	lmstudio_model: string | null;
	copilot_model: string | null;
	has_github_token: boolean;
	has_lmstudio_token: boolean;
};

type ConnectionResult = {
	ok: boolean;
	models: string[];
	error: string | null;
};

type SetupProps = {
	initial: ProviderSettings;
	onComplete: (settings: ProviderSettings) => void;
	onCancel?: () => void;
};

export function Setup({ initial, onComplete, onCancel }: SetupProps) {
	const [provider, setProvider] = useState<"lmstudio" | "copilot">(
		initial.selected_provider === "copilot" ? "copilot" : "lmstudio",
	);
	const [endpoint, setEndpoint] = useState(initial.lmstudio_url);
	const [githubToken, setGithubToken] = useState("");
	const [lmstudioToken, setLmstudioToken] = useState("");
	const [models, setModels] = useState<string[]>([]);
	const [model, setModel] = useState(
		provider === "copilot"
			? (initial.copilot_model ?? "")
			: (initial.lmstudio_model ?? ""),
	);
	const [testing, setTesting] = useState(false);
	const [saving, setSaving] = useState(false);
	const [tested, setTested] = useState(false);
	const [error, setError] = useState<string | null>(null);

	function chooseProvider(next: "lmstudio" | "copilot") {
		setProvider(next);
		setModels([]);
		setModel(
			next === "copilot"
				? (initial.copilot_model ?? "")
				: (initial.lmstudio_model ?? ""),
		);
		setTested(false);
		setError(null);
	}

	async function testConnection() {
		setTesting(true);
		setTested(false);
		setError(null);
		try {
			const response = await fetch("/api/settings/test", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					provider,
					endpoint: provider === "lmstudio" ? endpoint : null,
					token:
						provider === "copilot"
							? githubToken || null
							: lmstudioToken || null,
				}),
			});
			if (!response.ok) throw new Error("Connection test could not run");
			const result = (await response.json()) as ConnectionResult;
			if (!result.ok) throw new Error(result.error ?? "Connection failed");
			setModels(result.models);
			setModel((current) =>
				result.models.includes(current) ? current : (result.models[0] ?? ""),
			);
			setTested(true);
		} catch (reason) {
			setModels([]);
			setError(reason instanceof Error ? reason.message : "Connection failed");
		} finally {
			setTesting(false);
		}
	}

	async function save(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (!tested || !model) return;
		setSaving(true);
		setError(null);
		try {
			const response = await fetch("/api/settings", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					selected_provider: provider,
					lmstudio_url: endpoint,
					lmstudio_model:
						provider === "lmstudio" ? model : initial.lmstudio_model,
					copilot_model:
						provider === "copilot" ? model : initial.copilot_model,
					github_token: githubToken || null,
					lmstudio_token: lmstudioToken || null,
				}),
			});
			if (!response.ok) {
				const detail = (await response.json()) as { detail?: string };
				throw new Error(detail.detail ?? "Settings could not be saved");
			}
			onComplete((await response.json()) as ProviderSettings);
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : "Save failed");
		} finally {
			setSaving(false);
		}
	}

	return (
		<div className="setup-backdrop">
			<section className="setup-panel" aria-labelledby="setup-title">
				<header className="setup-header">
					<div>
						<span className="eyebrow">Private connection</span>
						<h1 id="setup-title">Connect Elena</h1>
					</div>
					{onCancel && (
						<button type="button" className="setup-close" onClick={onCancel}>
							Close
						</button>
					)}
				</header>

				<div className="provider-choice" aria-label="Provider">
					<button
						type="button"
						className={provider === "lmstudio" ? "is-selected" : ""}
						onClick={() => chooseProvider("lmstudio")}
					>
						LM Studio
					</button>
					<button
						type="button"
						className={provider === "copilot" ? "is-selected" : ""}
						onClick={() => chooseProvider("copilot")}
					>
						GitHub Copilot
					</button>
				</div>

				<form className="setup-form" onSubmit={save}>
					{provider === "lmstudio" ? (
						<>
							<label htmlFor="lmstudio-url">Server URL</label>
							<input
								id="lmstudio-url"
								type="url"
								value={endpoint}
								onChange={(event) => {
									setEndpoint(event.target.value);
									setTested(false);
								}}
								required
							/>
							<label htmlFor="lmstudio-token">
								API token <span>optional for local servers</span>
							</label>
							<input
								id="lmstudio-token"
								type="password"
								value={lmstudioToken}
								onChange={(event) => {
									setLmstudioToken(event.target.value);
									setTested(false);
								}}
								placeholder={
									initial.has_lmstudio_token ? "Stored in Windows" : "No token"
								}
							/>
						</>
					) : (
						<>
							<label htmlFor="github-token">
								GitHub token <span>optional when Copilot is already signed in</span>
							</label>
							<input
								id="github-token"
								type="password"
								value={githubToken}
								onChange={(event) => {
									setGithubToken(event.target.value);
									setTested(false);
								}}
								placeholder={
									initial.has_github_token
										? "Stored in Windows"
										: "Use existing Copilot login"
								}
							/>
						</>
					)}

					<button
						type="button"
						className="test-connection"
						onClick={testConnection}
						disabled={testing}
					>
						{testing ? "Testing..." : "Test connection and list models"}
					</button>

					{tested && (
						<>
							<label htmlFor="provider-model">Model</label>
							<select
								id="provider-model"
								value={model}
								onChange={(event) => setModel(event.target.value)}
								required
							>
								{models.map((item) => (
									<option key={item} value={item}>
										{item}
									</option>
								))}
							</select>
						</>
					)}

					{error && <p className="setup-error">{error}</p>}
					<button className="confirm-settings" type="submit" disabled={!tested || !model || saving}>
						{saving ? "Saving..." : "Confirm connection"}
					</button>
				</form>
				<p className="credential-note">
					Tokens are stored in Windows Credential Manager. Only endpoint and model
					choices are written to Elena's local settings.
				</p>
			</section>
		</div>
	);
}