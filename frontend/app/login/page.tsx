import Image from "next/image";
import { authConfigured } from "../../auth";

export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const params = await searchParams;
  const configured = authConfigured();
  return <main className="login-shell">
    <section className="login-form-side">
      <div className="login-card">
        <div className="login-topline"><div className="login-brand-type"><div className="original-wordmark"><Image src="/kycx-original-logo.png" width={4000} height={4000} alt="KYCX" priority/></div></div></div>
        <h1>Sign in</h1>
        <form action="/api/login" method="post">
          <label htmlFor="email">EMAIL ADDRESS</label>
          <input id="email" name="email" type="email" autoComplete="username" required defaultValue="admin@etil.nl" disabled={!configured}/>
          <label htmlFor="password">ACCESS PASSWORD</label>
          <input id="password" name="password" type="password" autoComplete="current-password" required disabled={!configured} placeholder="Enter your access password"/>
          {params.error === "invalid" && <div className="login-error" role="alert">The email or password didn’t match. Try again.</div>}
          {(!configured || params.error === "setup") && <div className="login-error" role="alert">Access is not configured. Set KYCX_ACCESS_PASSWORD and KYCX_SESSION_SECRET on the frontend service.</div>}
          <button type="submit" disabled={!configured}>Enter workspace <span aria-hidden="true">↗</span></button>
        </form>
        <div className="login-brand-footer"><span>POWERED BY</span><Image src="/ibc-group-official.png" width={120} height={55} alt="ibc group" priority/></div>
      </div>
      <div className="login-copyright">© 2026 KYCX · ibc group</div>
    </section>
  </main>;
}
