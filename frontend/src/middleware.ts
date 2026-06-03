import { type NextRequest, NextResponse } from "next/server";

const PROTECTED = ["/dashboard", "/incidents", "/integrations"];
const AUTH_PAGES = ["/login", "/signup"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isAuth = request.cookies.has("aiops_auth");

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
