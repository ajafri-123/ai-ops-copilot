import { type NextRequest, NextResponse } from "next/server";

const PROTECTED = ["/dashboard", "/incidents", "/integrations"];
const AUTH_PAGES = ["/login", "/signup"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Treat the session as valid only if the token-expiry cookie is present and
  // still in the future — not a cosmetic "logged in" flag.
  const expCookie = request.cookies.get("aiops_exp")?.value;
  const exp = expCookie ? Number(expCookie) : NaN;
  const isAuth = Number.isFinite(exp) && exp > Math.floor(Date.now() / 1000);

  const isProtected = PROTECTED.some((p) => pathname.startsWith(p));
  const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

  if (isProtected && !isAuth) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthPage && isAuth) {
    const dashUrl = request.nextUrl.clone();
    dashUrl.pathname = "/dashboard";
    return NextResponse.redirect(dashUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/incidents/:path*", "/integrations/:path*", "/login", "/signup"],
};
