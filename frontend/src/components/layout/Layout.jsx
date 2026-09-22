import { useEffect } from "react";
import { useLocation, Outlet } from "react-router-dom";
import NavBar from "./NavBar.jsx";
import Footer from "./Footer.jsx";

export default function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
  }, [pathname]);

  return (
    <>
      <NavBar />
      <Outlet />
      <Footer />
    </>
  );
}
