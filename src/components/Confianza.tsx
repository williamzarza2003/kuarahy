// Reseñas de ejemplo: el producto es ficticio y se aclara en la propia sección.
const resenas = [
  { nombre: 'Rocío G.', lugar: 'Minga Guazú', estrellas: 5, texto: 'Lo llené a las seis para ir a la obra y a las cuatro de la tarde todavía hacía ruido el hielo. La manija aguanta el peso lleno sin doblarse.', diseno: 'Siesta · 1,5 L · pico' },
  { nombre: 'Matías A.', lugar: 'Ciudad del Este', estrellas: 5, texto: 'Pedí el grabado con el nombre de mi papá para el Día del Padre. Quedó prolijo, no es un sticker: se siente el acero con la uña.', diseno: 'Carbón · 1 L · tapa vaso' },
  { nombre: 'Lorena V.', lugar: 'Hernandarias', estrellas: 4, texto: 'El pico cebador es lo mejor: servís con una mano y no chorrea. Y con la argolla de arriba lo cuelgo de la moto.', diseno: 'Lapacho · 1 L · pico' },
]

const preguntas = [
  { p: '¿Cuánto dura el hielo de verdad?', r: 'Lleno de hielo hasta el cuello, a la sombra y con 40° de máxima, quedan cubitos a las 24 horas. Al sol directo, calculá la mitad. Lo que más ayuda es enfriarlo antes con agua de la heladera.' },
  { p: '¿El grabado se borra?', r: 'No. Es grabado con láser: saca la pintura y deja el acero a la vista, así que no se despega ni se gasta con el lavado. Por eso no se puede cambiar después: revisá bien el nombre antes de pedirlo.' },
  { p: '¿Puedo cambiar de tapa después?', r: 'Sí. Las tres tapas (pico, vaso y mate) enroscan en el mismo cuello, así que podés comprar otra aparte y usar la que te convenga según el día.' },
  { p: '¿Se puede lavar en el lavavajillas?', r: 'Mejor no: el calor del lavavajillas castiga la pintura y la goma. Con agua tibia, detergente y un cepillo largo alcanza: la boca ancha de 6,5 cm lo deja pasar sin problema.' },
  { p: '¿Hacen envíos?', r: 'Retiro en el microcentro de Ciudad del Este o envío a todo el país por encomienda. El costo se calcula al confirmar la compra.' },
]

const Estrellas = ({ n }: { n: number }) => (
  <span className="estrellas" role="img" aria-label={`${n} de 5 estrellas`}>
    {Array.from({ length: 5 }, (_, i) => <span key={i} aria-hidden="true" className={i < n ? 'estrella estrella--llena' : 'estrella'}>★</span>)}
  </span>
)

/** Reseñas (de ejemplo), garantía y preguntas frecuentes. */
export default function Confianza() {
  return (
    <section className="confianza" aria-labelledby="titulo-resenas">
      <div className="contenedor">
        <div className="confianza__cabecera">
          <h2 id="titulo-resenas">Lo que dicen en la ronda</h2>
          <p className="confianza__demo">Reseñas de ejemplo: Kuarahy es una marca ficticia hecha para un portafolio.</p>
        </div>
        <ul className="resenas">
          {resenas.map((r) => (
            <li key={r.nombre} className="resena">
              <Estrellas n={r.estrellas} />
              <blockquote>{r.texto}</blockquote>
              <p className="resena__autor"><strong>{r.nombre}</strong> · {r.lugar}</p>
              <p className="resena__diseno">{r.diseno}</p>
            </li>
          ))}
        </ul>

        <div className="confianza__grilla">
          <div className="garantia">
            <h3>Garantía de 2 años</h3>
            <p>
              Si el termo pierde el vacío (se calienta por fuera o se forma agua entre las paredes) en los primeros
              dos años, te damos otro igual, con el mismo color y el mismo grabado. Sin vueltas: lo traés o lo mandás
              y lo cambiamos.
            </p>
            <p className="nota">No cubre golpes ni la pintura gastada por el uso.</p>
          </div>
          <div className="preguntas">
            <h3>Preguntas frecuentes</h3>
            {preguntas.map((x) => (
              <details key={x.p} className="pregunta">
                <summary>{x.p}</summary>
                <p>{x.r}</p>
              </details>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
