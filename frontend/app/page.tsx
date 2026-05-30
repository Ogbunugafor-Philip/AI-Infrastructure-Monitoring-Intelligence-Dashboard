import { redirect } from "next/navigation";

/** Root route: send users straight to the login landing page. */
export default function Home() {
  redirect("/login");
}
